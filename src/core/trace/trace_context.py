"""TraceContext：请求级追踪上下文。

这个模块在 Phase F1 负责把 C5 的“最小占位版”升级成真正可用于追踪的核心数据结构。
当前职责仍然只聚焦内存态数据收集与序列化，不负责落盘；JSON Lines 持久化由后续 F2 接手。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

_SUPPORTED_TRACE_TYPES = {"query", "ingestion"}


def _utc_now_iso() -> str:
    """返回统一的 UTC ISO 时间字符串。"""
    return datetime.now(UTC).isoformat()


def _make_json_safe(value: Any) -> Any:
    """把常见 Python 对象递归转换为 JSON 安全形态。

    做什么：
    - 递归处理 dict/list/tuple/set；
    - 把 `datetime` 统一转成 ISO 字符串；
    - 对其他不可直接序列化的对象回退为 `str(value)`。

    为什么：
    - F1 的 `to_dict()` 验收点要求“可 JSON 序列化”；
    - Trace 的 `details` 来自多处业务模块，未来很容易混入 `Path`、`datetime`
      或自定义对象，提前在这里兜底能减少后续 F2 落盘时的脆弱性。

    关键权衡：
    - 这里优先保证“可落盘、可展示”，而不是强保留所有原始对象类型；
    - 对未知对象使用字符串化，会损失部分结构信息，但可以避免整个 trace
      因一个字段不可序列化而失效。
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()

    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]

    return str(value)


@dataclass
class TraceContext:
    """请求级追踪上下文。

    做什么：
    - 为一次 query/ingestion 生成稳定的 `trace_id`；
    - 记录每个阶段的 `stage_name/details/status/elapsed_ms`；
    - 在请求结束时通过 `finish()` 冻结结束时间与总耗时；
    - 通过 `to_dict()` 输出可直接 JSON 序列化的结构化数据。

    为什么：
    - Query 链路和 Ingestion 链路都需要统一追踪契约，后续 Dashboard、
      JSON Lines 日志、问题排查才能建立在同一份数据形状之上；
    - 把生命周期与耗时统计放进 `TraceContext`，能避免各模块自行维护开始/结束时间，
      减少调用方重复代码和字段漂移。

    关键权衡：
    - `record_stage()` 保持 C5 阶段的调用签名不变，优先兼容现有大量调用点；
    - 总耗时使用 `perf_counter()` 计算，保证统计不受系统时钟跳变影响；
    - 对外暴露 `started_at/finished_at` 这类可读时间戳，同时内部保留 monotonic 时钟，
      兼顾可观测性与准确性。

    失败路径：
    - `trace_type` 非法时立即抛 `ValueError`，阻止错误分类进入追踪系统；
    - `stage_name` 非法时抛 `ValueError`，避免写入不可检索的脏阶段名；
    - `finish()` 之后再写阶段会抛 `RuntimeError`，避免“已结束请求仍继续追加数据”
      造成总耗时与阶段数据不一致。

    Args:
        trace_type: 追踪类型，仅支持 `query` 或 `ingestion`。
        trace_id: 可选外部注入的追踪 ID；未提供时自动生成。
        stages: 可选初始阶段列表，主要用于测试或反序列化场景。

    Example:
        >>> trace = TraceContext(trace_type="query")
        >>> trace.record_stage("dense_retrieval", {"result_count": 3}, elapsed_ms=12.5)
        >>> trace.finish()
        >>> payload = trace.to_dict()
        >>> payload["trace_type"]
        'query'
    """

    trace_type: str = "query"
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    stages: list[dict[str, Any]] = field(default_factory=list)
    started_at: str = field(init=False)
    finished_at: str | None = field(init=False, default=None)
    total_elapsed_ms: float | None = field(init=False, default=None)
    _started_monotonic: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """初始化生命周期字段并校验追踪类型。"""
        normalized_trace_type = str(self.trace_type).strip().lower()
        if normalized_trace_type not in _SUPPORTED_TRACE_TYPES:
            supported = ", ".join(sorted(_SUPPORTED_TRACE_TYPES))
            raise ValueError(f"trace_type must be one of: {supported}")

        self.trace_type = normalized_trace_type
        self.started_at = _utc_now_iso()
        self._started_monotonic = perf_counter()

        # 这里做一次深拷贝式标准化，避免外部把可变对象直接塞进来后又在别处修改，
        # 让 trace.stages 的内容在追踪上下文内部保持自洽。
        self.stages = [
            {
                "stage_name": str(stage.get("stage_name", "")).strip(),
                "status": str(stage.get("status", "ok")),
                "recorded_at": str(stage.get("recorded_at", _utc_now_iso())),
                "details": _make_json_safe(stage.get("details", {})),
                **(
                    {"elapsed_ms": float(stage["elapsed_ms"])}
                    if stage.get("elapsed_ms") is not None
                    else {}
                ),
            }
            for stage in self.stages
        ]

    @property
    def created_at(self) -> str:
        """兼容 C5 占位版字段名，等价于 `started_at`。"""
        return self.started_at

    @property
    def is_finished(self) -> bool:
        """返回当前 trace 是否已调用 `finish()`。"""
        return self.finished_at is not None

    def record_stage(
        self,
        stage_name: str,
        details: dict[str, Any] | None = None,
        elapsed_ms: float | int | None = None,
        status: str = "ok",
    ) -> None:
        """记录一个处理阶段。

        做什么：
        - 追加一条阶段记录到 `self.stages`；
        - 保持和 C5 版本一致的输入签名，让现有调用方无需改动；
        - 对 `details` 做 JSON-safe 规范化，为后续持久化提前兜底。

        为什么：
        - 现有 Query/Ingestion 调用点已经广泛使用 `trace.record_stage(...)`，
          F1 必须在增强能力的同时保持接口稳定，才能低风险落地。

        关键权衡：
        - 这里不强制要求每个阶段都提供 `elapsed_ms`，因为有些调用方只想记录事件；
        - 但如果提供了 `elapsed_ms`，会统一转换为 `float`，减少后续聚合时的分支判断。

        失败路径：
        - 空阶段名直接抛 `ValueError`；
        - 如果 trace 已经 `finish()`，抛 `RuntimeError` 暴露调用时序错误。
        """
        if self.is_finished:
            raise RuntimeError("cannot record stage after trace.finish()")

        if not isinstance(stage_name, str) or not stage_name.strip():
            raise ValueError("stage_name must be non-empty string")

        normalized_status = str(status or "ok").strip() or "ok"
        stage: dict[str, Any] = {
            "stage_name": stage_name.strip(),
            "status": normalized_status,
            "recorded_at": _utc_now_iso(),
            "details": _make_json_safe(dict(details or {})),
        }
        if elapsed_ms is not None:
            stage["elapsed_ms"] = float(elapsed_ms)

        self.stages.append(stage)

    def finish(self) -> None:
        """结束当前 trace 并冻结总耗时。

        做什么：
        - 写入 `finished_at`；
        - 基于 monotonic 时钟计算 `total_elapsed_ms`；
        - 保证后续 `elapsed_ms()` 和 `to_dict()` 返回稳定结果。

        为什么：
        - 请求结束后的 trace 应该是“可落盘、可展示、可复现”的静态快照，
          不能随着时间继续增长。

        关键权衡：
        - `finish()` 设计为幂等操作，重复调用不会重新计算或覆盖第一次结束时间；
        - 这样调用方即使在上层 finally 中重复收口，也不会制造不稳定数据。
        """
        if self.is_finished:
            return

        self.finished_at = _utc_now_iso()
        self.total_elapsed_ms = (perf_counter() - self._started_monotonic) * 1000.0

    def elapsed_ms(self, stage_name: str | None = None) -> float:
        """返回总耗时或某个阶段的耗时。

        做什么：
        - `stage_name is None`：返回整个 trace 的耗时；
        - `stage_name` 有值：返回最后一个同名阶段的 `elapsed_ms`。

        为什么：
        - 查询历史、Dashboard 瀑布图和调试脚本都需要一个统一入口来取耗时；
        - 选择“最后一个同名阶段”，是因为同名阶段在重试/多批次场景下最常见的诉求，
          往往是查看最终一次记录，而不是做聚合统计。

        失败路径：
        - 指定阶段不存在时抛 `KeyError`，提醒调用方名称写错或该阶段未记录；
        - 阶段存在但未提供 `elapsed_ms` 时返回 `0.0`，表示这是一条事件记录而非计时记录。

        Args:
            stage_name: 可选阶段名；为空时返回总耗时。

        Returns:
            float: 毫秒值。
        """
        if stage_name is None:
            if self.total_elapsed_ms is not None:
                return float(self.total_elapsed_ms)
            return (perf_counter() - self._started_monotonic) * 1000.0

        normalized_stage_name = str(stage_name).strip()
        if not normalized_stage_name:
            raise ValueError("stage_name must be non-empty string when provided")

        for stage in reversed(self.stages):
            if stage.get("stage_name") == normalized_stage_name:
                raw_elapsed = stage.get("elapsed_ms")
                if raw_elapsed is None:
                    return 0.0
                return float(raw_elapsed)

        raise KeyError(f"stage not found: {normalized_stage_name}")

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON 安全字典。

        说明：
        - F1 只负责生成结构化 payload，不负责文件写入；
        - `created_at` 作为兼容字段保留，值与 `started_at` 相同，
          这样可以减少 C5 期间潜在依赖方的迁移成本。
        """
        return {
            "trace_id": self.trace_id,
            "trace_type": self.trace_type,
            "started_at": self.started_at,
            "created_at": self.started_at,
            "finished_at": self.finished_at,
            "total_elapsed_ms": self.elapsed_ms() if self.total_elapsed_ms is None else float(self.total_elapsed_ms),
            "stages": _make_json_safe(list(self.stages)),
        }
