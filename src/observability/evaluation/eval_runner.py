"""H3 评估编排器：黄金测试集读取、检索执行与指标汇总。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.settings import Settings
from core.types import RetrievalResult
from libs.evaluator.base_evaluator import BaseEvaluator

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _utc_now_iso() -> str:
    """返回统一的 UTC ISO 时间戳。"""
    return datetime.now(UTC).isoformat()


def _normalize_string_list(values: Any) -> tuple[str, ...]:
    """把输入标准化为去空白、去空项的字符串元组。"""
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("list-like field must be list when provided")

    normalized: list[str] = []
    for index, item in enumerate(values):
        if not isinstance(item, str):
            raise ValueError(f"list-like field item[{index}] must be string")
        stripped = item.strip()
        if stripped:
            normalized.append(stripped)
    return tuple(normalized)


def _normalize_filters(filters: Any) -> dict[str, Any]:
    """标准化黄金测试集里的 filters 字段。"""
    if filters is None:
        return {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be dict when provided")
    return dict(filters)


@dataclass(frozen=True)
class GoldenTestCase:
    """黄金测试集中的单条用例。

    做什么：
    - 把 JSON 中的原始测试条目映射为强类型对象；
    - 统一承载 retrieval 评估所需的 query / filters / 期望命中信息；
    - 为后续 Ragas 评估预留 `generated_answer` 与 `ground_truth` 字段。

    为什么：
    - H3 阶段需要同时支持“检索指标”和“评估后端样本适配”两条链路；
    - 先把 JSON 入口收敛到 dataclass，可以把字段校验集中在一处，避免后面每个步骤都重复写 defensive code。
    """

    query: str
    expected_chunk_ids: tuple[str, ...] = ()
    expected_sources: tuple[str, ...] = ()
    filters: dict[str, Any] = field(default_factory=dict)
    generated_answer: str = ""
    ground_truth: str = ""

    def __post_init__(self) -> None:
        normalized_query = " ".join(str(self.query).split())
        if not normalized_query:
            raise ValueError("golden test case query must be non-empty string")

        object.__setattr__(self, "query", normalized_query)
        object.__setattr__(self, "expected_chunk_ids", tuple(self.expected_chunk_ids))
        object.__setattr__(self, "expected_sources", tuple(self.expected_sources))
        object.__setattr__(self, "filters", dict(self.filters))
        object.__setattr__(self, "generated_answer", str(self.generated_answer))
        object.__setattr__(self, "ground_truth", str(self.ground_truth))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GoldenTestCase":
        """从 JSON 条目构建单条黄金测试用例。"""
        if not isinstance(payload, dict):
            raise ValueError("golden test case must be dict")

        return cls(
            query=str(payload.get("query", "")),
            expected_chunk_ids=_normalize_string_list(payload.get("expected_chunk_ids")),
            expected_sources=_normalize_string_list(payload.get("expected_sources")),
            filters=_normalize_filters(payload.get("filters")),
            generated_answer=str(payload.get("generated_answer", "")),
            ground_truth=str(payload.get("ground_truth", "")),
        )


@dataclass(frozen=True)
class EvalQueryDetail:
    """单条 query 的评估明细。

    这里保留“输入是什么、召回了什么、是否命中、在哪一位命中、有没有降级错误”，
    目的是让 Dashboard 和命令行都能直接展示可读结果，而不是只有两个聚合分数。
    """

    query: str
    filters: dict[str, Any]
    expected_chunk_ids: tuple[str, ...]
    expected_sources: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]
    retrieved_sources: tuple[str, ...]
    hit: bool
    reciprocal_rank: float
    first_match_rank: int | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为稳定字典，便于 CLI 与后续页面直接消费。"""
        return {
            "query": self.query,
            "filters": dict(self.filters),
            "expected_chunk_ids": list(self.expected_chunk_ids),
            "expected_sources": list(self.expected_sources),
            "retrieved_chunk_ids": list(self.retrieved_chunk_ids),
            "retrieved_sources": list(self.retrieved_sources),
            "hit": self.hit,
            "reciprocal_rank": self.reciprocal_rank,
            "first_match_rank": self.first_match_rank,
            "error": self.error,
        }


@dataclass(frozen=True)
class EvalReport:
    """一次完整评估运行的结果报告。

    做什么：
    - 汇总 runner 自己计算的 retrieval 指标；
    - 附带逐 query 详情；
    - 保留 evaluator 后端返回的额外指标，供后续 Dashboard H4 展示。
    """

    test_set_path: str
    generated_at: str
    total: int
    hit_rate: float
    mrr: float
    details: tuple[EvalQueryDetail, ...]
    evaluator_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON 友好的结构。"""
        return {
            "test_set_path": self.test_set_path,
            "generated_at": self.generated_at,
            "total": self.total,
            "hit_rate": self.hit_rate,
            "mrr": self.mrr,
            "details": [detail.to_dict() for detail in self.details],
            "evaluator_metrics": dict(self.evaluator_metrics),
        }


class EvalRunner:
    """黄金测试集评估编排入口。

    做什么：
    - 读取 `golden_test_set.json`；
    - 逐条执行 `HybridSearch.search()`；
    - 计算与 retrieval 强相关的 `hit_rate` / `mrr`；
    - 把同一批检索结果转换成 evaluator 所需样本，交给 custom/ragas/composite 后端继续打分。

    为什么：
    - H3 的目标不是单纯“能调用一个评估器”，而是把“测试集 -> 检索运行 -> 聚合指标 -> 详细报告”串成可重复执行的闭环；
    - retrieval 指标必须由 runner 自己掌握，因为 `custom` 只会看 chunk_id，而真实黄金集还可能只标 `expected_sources`；
    - 这样即使某些 evaluator 的输入格式不同，主报告仍然能稳定产出统一的回归指标。

    关键权衡：
    - 当前项目到 H3 为止还没有正式的 answer generation 链路，因此给 Ragas 准备样本时，
      只能用“召回文本拼接”作为临时 `generated_answer` 代理。这能保证评估管线接通，但语义指标只适合作为占位和联调，不应过度解读。
    - 当检索后端暂时不可用或索引为空时，这里选择把单条 query 降级为“空结果 + error 字段”，
      而不是直接中断整次评估。这样脚本和 Dashboard 至少还能把问题暴露成一份完整报告。

    失败路径：
    - 测试集文件缺失、格式错误时抛出 `FileNotFoundError` / `ValueError`；
    - 单条检索失败时不抛出到整次运行，而是记录到 detail.error；
    - evaluator 后端执行失败时继续向上抛错，因为这类失败属于评估链路本身的问题，调用方需要明确知道。
    """

    def __init__(self, settings: Settings, hybrid_search: Any, evaluator: BaseEvaluator) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("EvalRunner requires Settings; call load_settings('config/settings.yaml') first")
        if not hasattr(hybrid_search, "search"):
            raise TypeError("hybrid_search must provide search(query, top_k, filters=None)")
        if not isinstance(evaluator, BaseEvaluator):
            raise TypeError("evaluator must implement BaseEvaluator")

        self.settings = settings
        self.hybrid_search = hybrid_search
        self.evaluator = evaluator

    def run(self, test_set_path: str) -> EvalReport:
        """执行一次黄金测试集评估并返回结构化报告。

        Args:
            test_set_path: 黄金测试集路径。支持绝对路径，也支持相对项目根目录的相对路径。

        Returns:
            EvalReport: 包含 hit_rate、mrr、逐 query 详情及评估后端附加指标的完整报告。
        """
        resolved_path = self._resolve_test_set_path(test_set_path)
        test_cases = self._load_test_cases(resolved_path)

        details: list[EvalQueryDetail] = []
        evaluator_samples: list[dict[str, Any]] = []
        hit_count = 0
        rr_sum = 0.0

        for case in test_cases:
            detail, evaluator_sample = self._run_single_case(case)
            details.append(detail)
            evaluator_samples.append(evaluator_sample)

            if detail.hit:
                hit_count += 1
            rr_sum += detail.reciprocal_rank

        total = len(details)
        hit_rate = (hit_count / total) if total else 0.0
        mrr = (rr_sum / total) if total else 0.0
        evaluator_metrics = self.evaluator.evaluate(evaluator_samples) if evaluator_samples else {}

        return EvalReport(
            test_set_path=str(resolved_path),
            generated_at=_utc_now_iso(),
            total=total,
            hit_rate=hit_rate,
            mrr=mrr,
            details=tuple(details),
            evaluator_metrics=dict(evaluator_metrics),
        )

    def _run_single_case(self, case: GoldenTestCase) -> tuple[EvalQueryDetail, dict[str, Any]]:
        """执行单条黄金用例，并同时生成详情和 evaluator 样本。"""
        try:
            results = self.hybrid_search.search(
                query=case.query,
                top_k=int(self.settings.retrieval.top_k),
                filters=case.filters or None,
            )
            error: str | None = None
        except RuntimeError as exc:
            # 这里显式把“索引为空 / 双路检索都暂时不可用”降级为空结果。
            # 评估脚本的职责是产出完整报告，而不是在第一条失败时直接中断。
            results = []
            error = f"{type(exc).__name__}: {exc}"

        retrieved_chunk_ids = tuple(item.chunk_id for item in results)
        retrieved_sources = tuple(self._extract_source_path(item) for item in results)
        first_match_rank = self._find_first_match_rank(results=results, case=case)
        reciprocal_rank = (1.0 / first_match_rank) if first_match_rank is not None else 0.0

        detail = EvalQueryDetail(
            query=case.query,
            filters=case.filters,
            expected_chunk_ids=case.expected_chunk_ids,
            expected_sources=case.expected_sources,
            retrieved_chunk_ids=retrieved_chunk_ids,
            retrieved_sources=retrieved_sources,
            hit=first_match_rank is not None,
            reciprocal_rank=reciprocal_rank,
            first_match_rank=first_match_rank,
            error=error,
        )

        return detail, self._build_evaluator_sample(case=case, results=results, error=error)

    def _build_evaluator_sample(
        self,
        *,
        case: GoldenTestCase,
        results: list[RetrievalResult],
        error: str | None,
    ) -> dict[str, Any]:
        """把单条 retrieval 结果转换成 evaluator 可消费的统一样本。

        说明：
        - `custom` evaluator 只严格使用 `retrieved_ids` 与 `golden_ids`；
        - `ragas` evaluator 还需要 `retrieved_chunks`、`generated_answer`、`ground_truth`；
        - 因此 runner 这里统一补齐两套字段，让上层不必知道每个后端的输入差异。
        """
        retrieved_chunks = [item.text for item in results]
        generated_answer = case.generated_answer.strip() or self._build_proxy_answer(results)
        ground_truth = case.ground_truth.strip()
        if not ground_truth:
            # H3 仍是 retrieval-first 项目，很多黄金集只会先标“期望来源”而非完整标准答案。
            # 为了让 Ragas 样本 shape 成立，这里退化为来源名字符串；这能打通链路，
            # 但不是严格的语义标准答案，后续 H4/H5 应逐步用人工标注答案替换。
            ground_truth = " | ".join(case.expected_sources)

        return {
            "query": case.query,
            "retrieved_ids": [item.chunk_id for item in results],
            "golden_ids": list(case.expected_chunk_ids),
            "retrieved_chunks": retrieved_chunks,
            "generated_answer": generated_answer,
            "ground_truth": ground_truth,
            "expected_sources": list(case.expected_sources),
            "filters": dict(case.filters),
            "error": error,
        }

    @staticmethod
    def _build_proxy_answer(results: list[RetrievalResult], max_chunks: int = 3) -> str:
        """在尚无正式生成链路时，用前几个召回片段拼接成临时答案代理。"""
        snippets: list[str] = []
        for item in results[:max_chunks]:
            text = " ".join(item.text.split())
            if text:
                snippets.append(text)
        return "\n\n".join(snippets)

    @staticmethod
    def _extract_source_path(result: RetrievalResult) -> str:
        """从检索结果 metadata 中提取 source_path，并统一成可比较字符串。"""
        return str(result.metadata.get("source_path", "")).strip()

    @classmethod
    def _find_first_match_rank(
        cls,
        *,
        results: list[RetrievalResult],
        case: GoldenTestCase,
    ) -> int | None:
        """查找第一条命中黄金答案的排名。

        命中规则：
        - 若 chunk_id 命中 `expected_chunk_ids`，视为相关；
        - 若 source_path 命中 `expected_sources`，也视为相关；
        - 两者是并集关系，因为黄金集在早期往往会先标来源，再逐步细化到 chunk 级别。
        """
        expected_ids = {item.strip() for item in case.expected_chunk_ids if item.strip()}
        expected_sources = {item.strip().lower() for item in case.expected_sources if item.strip()}

        for rank, item in enumerate(results, start=1):
            if item.chunk_id in expected_ids:
                return rank

            source_path = cls._extract_source_path(item).lower()
            if source_path and source_path in expected_sources:
                return rank

        return None

    @staticmethod
    def _resolve_test_set_path(raw_path: str) -> Path:
        """解析黄金测试集路径。

        这里优先支持：
        - 绝对路径；
        - 相对当前工作目录；
        - 相对项目根目录。
        """
        path = Path(str(raw_path).strip())
        if not str(path):
            raise ValueError("test_set_path must be non-empty string")

        if path.is_absolute():
            resolved = path
        else:
            cwd_candidate = (Path.cwd() / path).resolve()
            if cwd_candidate.exists():
                resolved = cwd_candidate
            else:
                resolved = (PROJECT_ROOT / path).resolve()

        if not resolved.exists():
            raise FileNotFoundError(f"golden test set not found: {resolved}")
        return resolved

    @staticmethod
    def _load_test_cases(test_set_path: Path) -> list[GoldenTestCase]:
        """从 JSON 文件读取黄金测试集。"""
        import json

        payload = json.loads(test_set_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("golden test set root must be object")

        raw_cases = payload.get("test_cases")
        if not isinstance(raw_cases, list):
            raise ValueError("golden test set must contain list field: test_cases")

        return [GoldenTestCase.from_dict(item) for item in raw_cases]
