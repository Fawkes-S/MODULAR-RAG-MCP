"""JSON Lines 日志与 TraceCollector 单元测试（F2）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.trace import TraceCollector, TraceContext  # noqa: E402
from observability.logger import get_logger, get_trace_logger, write_trace  # noqa: E402


def _read_jsonl_lines(path: Path) -> list[dict[str, object]]:
    """读取 jsonl 文件并返回逐行解析后的 JSON 对象。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_get_trace_logger_writes_jsonl_records(tmp_path: Path) -> None:
    """
    Given:
        一个指向临时 `traces.jsonl` 的 JSON Lines logger。
    When:
        使用该 logger 写入一条结构化 trace 字典。
    Then:
        目标文件应被创建，
        且文件中每一行都是可解析的单个 JSON 对象。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"
    logger = get_trace_logger(str(trace_file))

    logger.info({"trace_id": "trace-1", "trace_type": "query", "stages": []})
    for handler in logger.handlers:
        handler.flush()

    records = _read_jsonl_lines(trace_file)
    assert len(records) == 1
    assert records[0]["trace_id"] == "trace-1"
    assert records[0]["trace_type"] == "query"
    assert records[0]["stages"] == []


def test_write_trace_appends_multiple_json_lines(tmp_path: Path) -> None:
    """
    Given:
        同一个临时 trace 文件路径。
    When:
        连续两次调用 `write_trace()` 追加写入不同 trace。
    Then:
        文件应保留两条独立 JSON Lines 记录，
        而不是覆盖前一条内容。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"

    write_trace({"trace_id": "trace-a", "trace_type": "query", "stages": []}, trace_file=str(trace_file))
    write_trace({"trace_id": "trace-b", "trace_type": "ingestion", "stages": []}, trace_file=str(trace_file))

    records = _read_jsonl_lines(trace_file)
    assert [item["trace_id"] for item in records] == ["trace-a", "trace-b"]
    assert [item["trace_type"] for item in records] == ["query", "ingestion"]


def test_trace_collector_finishes_trace_and_persists_payload(tmp_path: Path) -> None:
    """
    Given:
        一个尚未 `finish()` 的 TraceContext，
        和一个指向临时 jsonl 文件的 TraceCollector。
    When:
        调用 `TraceCollector.collect(trace)`。
    Then:
        收集器应自动结束 trace、计算总耗时，
        并把包含 `trace_id/trace_type/finished_at/total_elapsed_ms/stages` 的 payload 写入文件。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"
    collector = TraceCollector(trace_file=str(trace_file))
    trace = TraceContext(trace_type="query")
    trace.record_stage("dense_retrieval", {"result_count": 2}, elapsed_ms=8.5)

    collector.collect(trace)

    assert trace.finished_at is not None
    assert trace.total_elapsed_ms is not None

    records = _read_jsonl_lines(trace_file)
    assert len(records) == 1
    payload = records[0]
    assert payload["trace_id"] == trace.trace_id
    assert payload["trace_type"] == "query"
    assert payload["finished_at"] == trace.finished_at
    assert float(payload["total_elapsed_ms"]) >= 0.0
    assert payload["stages"][0]["stage_name"] == "dense_retrieval"


def test_write_trace_rejects_non_dict_payload_and_collector_validates_type(tmp_path: Path) -> None:
    """
    Given:
        非法的 trace payload 与非法的 collector 输入对象。
    When:
        分别调用 `write_trace()` 和 `TraceCollector.collect()`。
    Then:
        应抛出明确异常，避免把错误数据静默写入 trace 文件。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"

    with pytest.raises(ValueError, match="trace_dict must be dict"):
        write_trace(["bad"], trace_file=str(trace_file))  # type: ignore[arg-type]

    collector = TraceCollector(trace_file=str(trace_file))
    with pytest.raises(TypeError, match="trace must be TraceContext"):
        collector.collect("bad")  # type: ignore[arg-type]


def test_get_logger_keeps_stderr_logger_compatible() -> None:
    """
    Given:
        项目内已有的普通文本 logger 使用方式。
    When:
        调用 `get_logger()` 获取同名 logger。
    Then:
        返回对象应仍然可用，
        且至少保留一个 handler，确保 F2 没有破坏原有 stderr 日志路径。
    """
    logger = get_logger("tests.compat.logger")

    assert logger.name == "tests.compat.logger"
    assert logger.handlers
