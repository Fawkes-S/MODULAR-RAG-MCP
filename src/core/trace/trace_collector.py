"""TraceCollector：收集并持久化 TraceContext。"""

from __future__ import annotations

from dataclasses import dataclass

from core.trace.trace_context import TraceContext
from observability.logger import write_trace


@dataclass(frozen=True)
class TraceCollector:
    """追踪收集器。

    做什么：
    - 接收一个内存态 `TraceContext`；
    - 确保 trace 已 `finish()`；
    - 将 `trace.to_dict()` 的结果追加写入 JSON Lines 文件。

    为什么：
    - `TraceContext` 负责“收集数据”，`TraceCollector` 负责“收口并持久化”，
      这样 Query / Ingestion 调用方只需要在请求末尾调用一个明确动作，
      不必关心文件写入细节。

    关键权衡：
    - 收集器不主动吞掉写文件异常；若 trace 文件不可写，应让上层明确感知，
      这样问题会在开发和测试阶段暴露，而不是悄悄丢失追踪数据。

    Args:
        trace_file: 目标 JSON Lines 文件路径；默认写入 `logs/traces.jsonl`。
    """

    trace_file: str = "logs/traces.jsonl"

    def collect(self, trace: TraceContext) -> None:
        """完成 trace 并持久化到 JSON Lines 文件。

        Args:
            trace: 待收集的追踪上下文。

        Raises:
            TypeError: 当 `trace` 不是 `TraceContext` 时抛出，阻止错误对象被误写入日志。
        """
        if not isinstance(trace, TraceContext):
            raise TypeError("trace must be TraceContext")

        # 收集器是“请求生命周期的最后一步”，因此这里统一负责 finish，
        # 让调用方不必记住“先 finish 再写文件”的顺序细节。
        trace.finish()
        write_trace(trace.to_dict(), trace_file=self.trace_file)
