"""Fusion：RRF（Reciprocal Rank Fusion）融合实现（D4）。"""

from __future__ import annotations

from core.types import RetrievalResult


class RRFFusion:
    """基于 RRF 的检索结果融合器。

    做什么：
    - 接收 Dense 与 Sparse 两路 `RetrievalResult` 排名列表；
    - 按 RRF 公式计算融合分数并统一排序；
    - 输出可直接被后续编排层消费的 Top-K 结果。

    为什么：
    - Dense 与 Sparse 的原始 score 量纲不同，直接相加不可比；
      RRF 只依赖“名次”信息，能稳定融合异构检索后端结果。

    关键权衡：
    - 采用“名次融合”而不是“分数归一化融合”，牺牲一部分分值细粒度信息，
      换取更强的跨后端鲁棒性和可解释性。
    - 同分情况下按 `best_rank` 再按 `chunk_id` 排序，保证输出 deterministic。

    失败路径：
    - 输入列表 shape 非法或 `top_k/k` 非法会抛出 `ValueError`；
    - 任何脏数据都在 Fusion 入口 fail-fast，避免污染下游排序。
    """

    DEFAULT_K = 60

    def __init__(self, default_k: int = DEFAULT_K) -> None:
        """初始化 RRF 融合器。

        Args:
            default_k: RRF 平滑参数，越大表示“后排名次”的贡献衰减越慢。
        """
        self.default_k = self._normalize_k(default_k)

    def fuse(
        self,
        dense_results: list[RetrievalResult],
        sparse_results: list[RetrievalResult],
        top_k: int,
        k: int | None = None,
    ) -> list[RetrievalResult]:
        """融合 Dense/Sparse 排名并返回统一 Top-K。

        做什么：
        - 对两路候选分别按输入顺序赋予 rank（从 1 开始）；
        - 按 `1 / (k + rank)` 计算每条候选在该路的贡献分；
        - 对同一 `chunk_id` 跨路累加贡献，得到最终融合分数。

        为什么：
        - 该方法保证在 Dense/Sparse 只要任一路召回到命中项，它都能进入候选；
          若两路都命中，同一 chunk 会获得更高融合分，从而自然上浮。

        关键权衡：
        - 若同一路出现重复 chunk_id，仅保留第一次出现（即更高 rank）；
          这样能避免重复项人为抬高分数。

        失败路径：
        - 参数不合法时直接抛 `ValueError`，调用方应在更上层转换为用户可读错误。

        Args:
            dense_results: 稠密检索结果（按相关性降序）。
            sparse_results: 稀疏检索结果（按相关性降序）。
            top_k: 返回候选数量上限。
            k: 可选覆盖默认 RRF 参数；为空时使用构造器 `default_k`。

        Returns:
            list[RetrievalResult]: 融合后按分数降序排序的结果列表。
        """
        normalized_top_k = self._normalize_top_k(top_k)
        normalized_k = self._normalize_k(self.default_k if k is None else k)

        dense = self._normalize_route_results(dense_results, route_name="dense_results")
        sparse = self._normalize_route_results(sparse_results, route_name="sparse_results")

        score_by_id: dict[str, float] = {}
        best_rank_by_id: dict[str, int] = {}
        payload_by_id: dict[str, RetrievalResult] = {}

        for route_results in (dense, sparse):
            for rank, item in enumerate(route_results, start=1):
                chunk_id = item.chunk_id
                rrf_score = 1.0 / (normalized_k + rank)
                score_by_id[chunk_id] = score_by_id.get(chunk_id, 0.0) + rrf_score

                # 同一 chunk 在不同路的 payload 理论应一致；这里以首次出现为准，
                # 兼顾稳定性与低复杂度，不做额外合并逻辑。
                if chunk_id not in payload_by_id:
                    payload_by_id[chunk_id] = item

                previous_best_rank = best_rank_by_id.get(chunk_id)
                if previous_best_rank is None or rank < previous_best_rank:
                    best_rank_by_id[chunk_id] = rank

        ranked_ids = sorted(
            score_by_id.keys(),
            key=lambda chunk_id: (
                -score_by_id[chunk_id],          # 主排序：融合分数越高越靠前
                best_rank_by_id[chunk_id],       # 次排序：最佳名次越靠前越优先
                chunk_id,                        # 兜底排序：确保同分时 deterministic
            ),
        )

        fused_results: list[RetrievalResult] = []
        for chunk_id in ranked_ids[:normalized_top_k]:
            payload = payload_by_id[chunk_id]
            fused_results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    score=score_by_id[chunk_id],
                    text=payload.text,
                    metadata=dict(payload.metadata),
                )
            )
        return fused_results

    @staticmethod
    def _normalize_top_k(top_k: int) -> int:
        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be positive int")
        return top_k

    @staticmethod
    def _normalize_k(k: int) -> int:
        if not isinstance(k, int) or k < 0:
            raise ValueError("k must be non-negative int")
        return k

    @staticmethod
    def _normalize_route_results(
        results: list[RetrievalResult],
        route_name: str,
    ) -> list[RetrievalResult]:
        if not isinstance(results, list):
            raise ValueError(f"{route_name} must be list[RetrievalResult]")

        deduplicated: list[RetrievalResult] = []
        seen_ids: set[str] = set()
        for idx, item in enumerate(results):
            if not isinstance(item, RetrievalResult):
                raise ValueError(f"{route_name}[{idx}] must be RetrievalResult")
            if item.chunk_id in seen_ids:
                # 同一路重复命中时，保留第一次（更高 rank）并丢弃后续重复项。
                continue
            deduplicated.append(item)
            seen_ids.add(item.chunk_id)
        return deduplicated
