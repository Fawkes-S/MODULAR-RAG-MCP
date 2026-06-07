"""可观测性日志工具。

这个模块同时承担两类职责：
1. 继续提供面向 `stderr` 的普通文本 logger，供 CLI / Server / Pipeline 打印人类可读日志；
2. 提供面向 `logs/traces.jsonl` 的结构化 trace writer，供 TraceCollector 以 JSON Lines 形式持久化追踪记录。

F2 只实现“本地文件追加写入”的最小闭环，不引入外部日志系统，保持零依赖与可调试性。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

_DEFAULT_TRACE_FILE = "logs/traces.jsonl"


class JsonLineFormatter(logging.Formatter):
    """把单条日志记录格式化为 JSON Lines 所需的单行 JSON 字符串。

    做什么：
    - 从 `LogRecord.msg` 中提取结构化 dict；
    - 补充最小日志元信息，便于后续人工排障；
    - 保证每条日志最终都是单行 JSON，适合顺序追加到 `.jsonl` 文件。

    为什么：
    - Dashboard 与命令行工具都依赖“一行一个 JSON 对象”的文件约定；
    - 使用 logging formatter 而不是手写 `open(...).write(...)`，可以复用 logger 的 handler、
      flush 与追加写入能力，也便于后续扩展到更多 sink。

    关键权衡：
    - 这里优先输出 trace payload 本身，不额外包裹复杂嵌套字段，避免后续解析时多一层解包；
    - 仅补充 `logged_at/logger/level` 这类通用元数据，保持输出足够轻量。
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = record.msg if isinstance(record.msg, dict) else {"message": record.getMessage()}
        normalized = _make_json_safe(payload)
        if not isinstance(normalized, dict):
            normalized = {"message": normalized}

        if "logged_at" not in normalized:
            normalized["logged_at"] = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        if "logger" not in normalized:
            normalized["logger"] = record.name
        if "level" not in normalized:
            normalized["level"] = record.levelname

        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def _make_json_safe(value: Any) -> Any:
    """把任意常见 Python 对象转换成可 JSON 序列化的形式。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    return str(value)


def get_logger(name: str) -> logging.Logger:
    """返回写入 `stderr` 的普通文本 logger。

    做什么：
    - 保持项目里已有 `get_logger()` 行为不变；
    - 避免 F2 引入结构化文件日志后，破坏现有 CLI / Pipeline 的人工可读输出。
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_trace_logger(trace_file: str = _DEFAULT_TRACE_FILE) -> logging.Logger:
    """返回一个配置为 JSON Lines 文件输出的 logger。

    做什么：
    - 为指定 trace 文件创建独立的 file logger；
    - 自动创建父目录；
    - 复用单例 logger，避免多次调用后重复追加多个 handler。

    为什么：
    - F2 的目标是把 `trace.to_dict()` 稳定落到本地文件；
    - 后续 Query / Ingestion 链路都可以通过这一个入口拿到文件 logger，而不需要各自管理文件句柄。

    失败路径：
    - 路径不可创建或文件无法打开时，让 `FileHandler` 原始异常直接暴露，
      这样调用方能明确知道是权限/路径问题，而不是无声丢日志。
    """
    resolved_path = Path(trace_file).expanduser()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    logger_name = f"observability.trace::{resolved_path.resolve()}"
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(resolved_path, mode="a", encoding="utf-8")
    handler.setFormatter(JsonLineFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def write_trace(trace_dict: dict[str, Any], trace_file: str = _DEFAULT_TRACE_FILE) -> None:
    """把单条 trace 追加写入 JSON Lines 文件。

    做什么：
    - 对输入 payload 做基本 shape 校验；
    - 委托 `get_trace_logger()` 获取稳定的文件 logger；
    - 以“一行一个 JSON 对象”的方式追加写入。

    为什么：
    - 将“如何把 trace payload 写入文件”的细节统一收敛到一个函数，
      后续 `TraceCollector` 或脚本都可以复用，避免散落的文件写入实现。

    关键权衡：
    - 这里不自动帮调用方补业务字段，如 `trace_id` / `trace_type`；
      如果缺字段，说明上游 trace 构建就有问题，应尽早暴露。

    Raises:
        ValueError: 当传入 payload 不是 dict 时抛出，阻止脏数据进入 trace 文件。
    """
    if not isinstance(trace_dict, dict):
        raise ValueError("trace_dict must be dict")

    logger = get_trace_logger(trace_file=trace_file)
    logger.info(_make_json_safe(trace_dict))

    # 这里显式 flush，确保 CLI / 测试在写完后立刻能读到文件内容，
    # 避免因为缓冲区未刷盘造成“日志似乎没有生成”的假象。
    for handler in logger.handlers:
        handler.flush()
