"""TraceContext 最小实现（C5 占位版）。

说明：
- 当前阶段仅提供最小可用能力：trace_id 生成 + record_stage 记录。
- 更完整的耗时统计、finish 生命周期与结构化序列化将在 Phase F 扩展。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class TraceContext:
    """请求级追踪上下文。

    做什么：
    - 为一次 ingestion/query 处理生成唯一 trace_id。
    - 收集阶段级记录（stage_name + details + elapsed_ms）。

    为什么：
    - C5 需要先提供统一追踪入口，避免后续 Transform/Pipeline 各自发明日志结构。

    关键权衡：
    - 当前实现追求最小可用，优先稳定接口；复杂统计逻辑延后到 F 阶段。

    失败路径：
    - `record_stage` 对输入做轻量校验，错误参数直接抛 ValueError。

    Args:
        trace_type: 追踪类型，通常为 `ingestion` 或 `query`。
    """

    trace_type: str = "ingestion"
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    stages: list[dict[str, Any]] = field(default_factory=list)

    def record_stage(
        self,
        stage_name: str,
        details: dict[str, Any] | None = None,
        elapsed_ms: float | int | None = None,
        status: str = "ok",
    ) -> None:
        """记录一个处理阶段。"""
        if not isinstance(stage_name, str) or not stage_name.strip():
            raise ValueError("stage_name must be non-empty string")

        stage: dict[str, Any] = {
            "stage_name": stage_name.strip(),
            "status": status,
            "recorded_at": datetime.now(UTC).isoformat(),
            "details": dict(details or {}),
        }
        if elapsed_ms is not None:
            stage["elapsed_ms"] = float(elapsed_ms)

        self.stages.append(stage)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "trace_id": self.trace_id,
            "trace_type": self.trace_type,
            "created_at": self.created_at,
            "stages": list(self.stages),
        }
