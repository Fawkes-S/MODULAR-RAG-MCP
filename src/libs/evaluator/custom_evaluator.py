"""轻量自定义评估器：计算 hit_rate 与 mrr。"""

from __future__ import annotations

from typing import Any

from libs.evaluator.base_evaluator import BaseEvaluator


class CustomEvaluator(BaseEvaluator):
    """最小可用评估器实现。

    设计目标：
    - 提供稳定、可复现的离线指标，便于早期开发回归验证；
    - 以 `retrieved_ids` 与 `golden_ids` 的匹配关系计算 hit_rate / mrr。
    """

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        """对样本集计算聚合指标和逐条详情。

        Args:
            samples: 评估样本列表。每条样本字段约定：
                - `query`: 查询文本（仅用于结果展示）
                - `retrieved_ids`: 检索结果 ID 列表（有序）
                - `golden_ids`: 标注答案 ID 列表
            trace: 可选链路上下文，占位给后续可观测扩展。

        Returns:
            dict[str, Any]: 结构化评估结果，包含：
                - `hit_rate`: 命中率（命中样本数 / 总样本数）
                - `mrr`: 平均倒数排名
                - `total`: 样本总数
                - `details`: 逐样本指标详情（hit / rr）

        Raises:
            ValueError: 当样本缺失 `retrieved_ids` 或 `golden_ids` 时抛出。
        """
        total = len(samples)
        if total == 0:
            return {"hit_rate": 0.0, "mrr": 0.0, "total": 0, "details": []}

        details: list[dict[str, Any]] = []
        hit_count = 0
        rr_sum = 0.0

        for index, sample in enumerate(samples):
            if "retrieved_ids" not in sample or "golden_ids" not in sample:
                raise ValueError(f"sample[{index}] missing required keys: retrieved_ids/golden_ids")

            retrieved_ids = sample.get("retrieved_ids") or []
            if not isinstance(retrieved_ids, list):
                raise ValueError(f"sample[{index}].retrieved_ids must be list")
            golden_ids_raw = sample.get("golden_ids") or []
            if not isinstance(golden_ids_raw, list):
                raise ValueError(f"sample[{index}].golden_ids must be list")

            # 这里显式要求字符串列表，避免把 `"chunk_1"` 误当成可迭代对象拆成字符集合。
            golden_ids = set()
            for golden_index, golden_id in enumerate(golden_ids_raw):
                if not isinstance(golden_id, str):
                    raise ValueError(
                        f"sample[{index}].golden_ids[{golden_index}] must be string"
                    )
                if golden_id:
                    golden_ids.add(golden_id)

            first_match_rank = self._first_match_rank(retrieved_ids, golden_ids)
            hit = first_match_rank is not None
            rr = 1.0 / first_match_rank if first_match_rank is not None else 0.0

            if hit:
                hit_count += 1
            rr_sum += rr

            details.append(
                {
                    "query": sample.get("query", ""),
                    "hit": hit,
                    "rr": rr,
                    "first_match_rank": first_match_rank,
                }
            )

        return {
            "hit_rate": hit_count / total,
            "mrr": rr_sum / total,
            "total": total,
            "details": details,
        }

    @staticmethod
    def _first_match_rank(retrieved_ids: list[str], golden_ids: set[str]) -> int | None:
        """返回第一个命中 golden 的 1-based 排名。"""
        for i, item_id in enumerate(retrieved_ids, start=1):
            if item_id in golden_ids:
                return i
        return None
