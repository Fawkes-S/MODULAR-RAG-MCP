"""TraceContext 单元测试（F1）。"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.trace.trace_context import TraceContext  # noqa: E402


def test_trace_context_defaults_to_query_and_supports_explicit_ingestion() -> None:
    """
    Given:
        一个未显式传入 trace_type 的 TraceContext，
        以及一个显式传入 `trace_type="ingestion"` 的 TraceContext。
    When:
        分别读取它们的生命周期字段与序列化结果。
    Then:
        默认实例应使用 `query`；
        显式实例应保留 `ingestion`；
        `created_at` 兼容字段应与 `started_at` 保持一致。
    """
    query_trace = TraceContext()
    ingestion_trace = TraceContext(trace_type="ingestion")

    assert query_trace.trace_type == "query"
    assert ingestion_trace.trace_type == "ingestion"
    assert query_trace.created_at == query_trace.started_at
    assert ingestion_trace.to_dict()["trace_type"] == "ingestion"


def test_trace_context_returns_stage_elapsed_and_live_total_elapsed() -> None:
    """
    Given:
        一个仍在执行中的 TraceContext，
        且其中写入了带 `elapsed_ms` 的阶段记录。
    When:
        调用 `elapsed_ms()` 读取总耗时，
        并调用 `elapsed_ms(stage_name)` 读取指定阶段耗时。
    Then:
        总耗时应返回一个非负毫秒值；
        阶段耗时应返回写入时的浮点值；
        未提供 `elapsed_ms` 的事件型阶段应返回 0.0。
    """
    trace = TraceContext(trace_type="query")
    trace.record_stage("dense_retrieval", {"result_count": 2}, elapsed_ms=12.5)
    trace.record_stage("rerank", {"backend": "none"})

    assert trace.elapsed_ms() >= 0.0
    assert trace.elapsed_ms("dense_retrieval") == pytest.approx(12.5)
    assert trace.elapsed_ms("rerank") == pytest.approx(0.0)


def test_trace_context_finish_populates_finished_timestamp_and_total_elapsed() -> None:
    """
    Given:
        一个已经记录过阶段的 TraceContext。
    When:
        调用 `finish()` 完成追踪。
    Then:
        应写入 `finished_at` 与 `total_elapsed_ms`；
        `elapsed_ms()` 应返回冻结后的总耗时；
        重复调用 `finish()` 不应改写第一次结束结果。
    """
    trace = TraceContext(trace_type="ingestion")
    trace.record_stage("load", {"pages": 3}, elapsed_ms=8.0)

    trace.finish()
    first_finished_at = trace.finished_at
    first_total_elapsed = trace.total_elapsed_ms
    trace.finish()

    assert first_finished_at is not None
    assert first_total_elapsed is not None
    assert trace.finished_at == first_finished_at
    assert trace.total_elapsed_ms == pytest.approx(first_total_elapsed)
    assert trace.elapsed_ms() == pytest.approx(first_total_elapsed)


def test_trace_context_to_dict_is_json_safe_and_contains_stage_payload() -> None:
    """
    Given:
        一个阶段详情中包含 `datetime`、`set` 与普通标量的 TraceContext。
    When:
        调用 `finish()` 后再执行 `to_dict()` 与 `json.dumps()`。
    Then:
        输出应包含 F1 规定的核心字段；
        `details` 中的复杂对象应被转换成 JSON 安全值；
        整个结果可以被 JSON 序列化。
    """
    trace = TraceContext(trace_type="query")
    trace.record_stage(
        "query_processing",
        {
            "keywords": {"azure", "openai"},
            "recorded_at": datetime(2026, 6, 7, tzinfo=UTC),
            "top_k": 5,
        },
        elapsed_ms=3.2,
    )
    trace.finish()

    payload = trace.to_dict()
    stage = payload["stages"][0]

    assert payload["trace_id"] == trace.trace_id
    assert payload["trace_type"] == "query"
    assert payload["started_at"] == trace.started_at
    assert payload["finished_at"] == trace.finished_at
    assert payload["total_elapsed_ms"] == pytest.approx(trace.total_elapsed_ms or 0.0)
    assert stage["stage_name"] == "query_processing"
    assert sorted(stage["details"]["keywords"]) == ["azure", "openai"]
    assert stage["details"]["recorded_at"] == "2026-06-07T00:00:00+00:00"
    json.dumps(payload)


def test_trace_context_rejects_invalid_inputs_and_post_finish_mutation() -> None:
    """
    Given:
        非法的 trace_type / stage_name 输入，
        以及一个已经 `finish()` 的 TraceContext。
    When:
        依次触发初始化、阶段记录、阶段读取和结束后的追加写入。
    Then:
        应抛出明确异常，阻止不合法追踪数据进入后续日志与 Dashboard。
    """
    with pytest.raises(ValueError, match="trace_type must be one of"):
        TraceContext(trace_type="other")

    trace = TraceContext(trace_type="query")

    with pytest.raises(ValueError, match="stage_name must be non-empty string"):
        trace.record_stage("")

    with pytest.raises(KeyError, match="stage not found"):
        trace.elapsed_ms("missing_stage")

    trace.finish()
    with pytest.raises(RuntimeError, match="cannot record stage after trace.finish"):
        trace.record_stage("late_stage")
