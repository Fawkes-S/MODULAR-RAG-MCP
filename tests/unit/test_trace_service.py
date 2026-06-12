"""TraceService 单元测试（G5）。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard.services.trace_service import TraceService  # noqa: E402


def test_trace_service_reads_ingestion_traces_sorts_desc_and_aggregates_stages(tmp_path: Path) -> None:
    """
    Given:
        一个临时 `settings.yaml`，其 `observability.trace_file` 指向测试专用 `traces.jsonl`；
        且文件中同时包含 query trace、ingestion trace 和一行坏 JSON。
    When:
        调用 `TraceService.load_traces(trace_type="ingestion")` 读取并过滤记录。
    Then:
        - 仅返回 ingestion 记录；
        - 按开始时间倒序排列；
        - 能从阶段 details 中提取 source_path/collection；
        - `transform` 多次出现时应聚合耗时；
        - 坏 JSON 行应被跳过并计数。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    trace_file.write_text(
        "\n".join(
            [
                (
                    '{"trace_id":"trace-old","trace_type":"ingestion","started_at":"2026-06-10T09:00:00+00:00",'
                    '"finished_at":"2026-06-10T09:00:01+00:00","total_elapsed_ms":1000.0,'
                    '"stages":[{"stage_name":"pipeline.request","details":{"source_path":"Q:/docs/alpha.pdf","collection":"demo"}},'
                    '{"stage_name":"load","elapsed_ms":100.0,"status":"ok","details":{"method":"pdf","provider":"PdfLoader"}},'
                    '{"stage_name":"transform","elapsed_ms":30.0,"status":"ok","details":{"method":"ChunkRefiner","provider":"ChunkRefiner","source_stage":"transform.ChunkRefiner"}},'
                    '{"stage_name":"transform","elapsed_ms":20.0,"status":"ok","details":{"method":"MetadataEnricher","provider":"MetadataEnricher","source_stage":"transform.MetadataEnricher"}},'
                    '{"stage_name":"upsert","elapsed_ms":50.0,"status":"ok","details":{"method":"vector_store_upsert","provider":"chroma"}}]}'
                ),
                "not-json-at-all",
                (
                    '{"trace_id":"trace-query","trace_type":"query","started_at":"2026-06-11T08:00:00+00:00",'
                    '"finished_at":"2026-06-11T08:00:00+00:00","total_elapsed_ms":1.0,"stages":[]}'
                ),
                (
                    '{"trace_id":"trace-new","trace_type":"ingestion","started_at":"2026-06-11T10:00:00+00:00",'
                    '"finished_at":"2026-06-11T10:00:02+00:00","total_elapsed_ms":2000.0,'
                    '"stages":[{"stage_name":"pipeline.request","details":{"source_path":"Q:/docs/beta.pdf","collection":"prod"}},'
                    '{"stage_name":"load","elapsed_ms":120.0,"status":"ok","details":{"method":"pdf","provider":"PdfLoader"}},'
                    '{"stage_name":"split","elapsed_ms":80.0,"status":"ok","details":{"method":"recursive","provider":"RecursiveCharacterTextSplitter"}},'
                    '{"stage_name":"embed","elapsed_ms":250.0,"status":"ok","details":{"method":"batch_dense_sparse_encode","provider":"huggingface_local"}},'
                    '{"stage_name":"upsert","elapsed_ms":90.0,"status":"error","details":{"method":"vector_store_upsert","provider":"chroma"}}]}'
                ),
            ]
        ),
        encoding="utf-8",
    )

    settings_path = tmp_path / "config" / "settings.yaml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        "\n".join(
            [
                "llm:",
                "  provider: openai",
                "embedding:",
                "  provider: huggingface_local",
                "vector_store:",
                "  provider: chroma",
                "retrieval:",
                "  top_k: 5",
                "rerank:",
                "  provider: none",
                "evaluation:",
                "  provider: local",
                "observability:",
                f"  trace_file: {trace_file.as_posix()}",
                "  log_level: INFO",
                "dashboard:",
                "  traces_dir: logs",
                "  auto_refresh: true",
                "  refresh_interval: 5",
            ]
        ),
        encoding="utf-8",
    )

    service = TraceService(settings_path=settings_path)
    result = service.load_traces(trace_type="ingestion")

    assert result.trace_file == str(trace_file)
    assert result.skipped_lines == 1
    assert [item.trace_id for item in result.records] == ["trace-new", "trace-old"]
    assert result.records[0].file_name == "beta.pdf"
    assert result.records[0].collection == "prod"
    assert result.records[0].status == "failed"
    assert result.records[1].status == "success"

    transform_stage = next(stage for stage in result.records[1].stage_breakdown if stage.stage_name == "transform")
    assert transform_stage.present is True
    assert transform_stage.elapsed_ms == 50.0
    assert transform_stage.source_stages == ("transform.ChunkRefiner", "transform.MetadataEnricher")


def test_trace_service_returns_empty_result_when_trace_file_missing(tmp_path: Path) -> None:
    """
    Given:
        一个 settings 文件，但其中指向的 trace 文件尚不存在。
    When:
        调用 `TraceService.load_traces()`。
    Then:
        service 应返回空记录列表与 0 条坏行计数，
        而不是因为“还没有 trace 文件”直接抛异常。
    """
    missing_trace_file = tmp_path / "logs" / "traces.jsonl"
    settings_path = tmp_path / "config" / "settings.yaml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        "\n".join(
            [
                "llm:",
                "  provider: openai",
                "embedding:",
                "  provider: huggingface_local",
                "vector_store:",
                "  provider: chroma",
                "retrieval:",
                "  top_k: 5",
                "rerank:",
                "  provider: none",
                "evaluation:",
                "  provider: local",
                "observability:",
                f"  trace_file: {missing_trace_file.as_posix()}",
                "  log_level: INFO",
                "dashboard:",
                "  traces_dir: logs",
                "  auto_refresh: false",
                "  refresh_interval: 9",
            ]
        ),
        encoding="utf-8",
    )

    service = TraceService(settings_path=settings_path)
    result = service.load_traces(trace_type="ingestion")
    runtime = service.get_runtime_config()

    assert result.trace_file == str(missing_trace_file)
    assert result.records == []
    assert result.skipped_lines == 0
    assert runtime.auto_refresh is False
    assert runtime.refresh_interval == 9


def test_trace_service_marks_pipeline_skip_trace_as_skipped(tmp_path: Path) -> None:
    """
    Given:
        一条 ingestion trace，其阶段列表中包含 `pipeline.skip` 事件。
    When:
        通过 `TraceService.load_traces(trace_type="ingestion")` 读取该记录。
    Then:
        这条 trace 的整体状态应被标记为 `skipped`，
        避免 Dashboard 把“增量跳过”误显示成普通成功。
    """
    trace_file = tmp_path / "logs" / "traces.jsonl"
    trace_file.parent.mkdir(parents=True, exist_ok=True)
    trace_file.write_text(
        (
            '{"trace_id":"trace-skip","trace_type":"ingestion","started_at":"2026-06-12T09:00:00+00:00",'
            '"finished_at":"2026-06-12T09:00:00+00:00","total_elapsed_ms":3.0,'
            '"stages":[{"stage_name":"pipeline.request","details":{"source_path":"Q:/docs/skip.pdf","collection":"demo"}},'
            '{"stage_name":"pipeline.skip","details":{"reason":"integrity_hit","source_path":"Q:/docs/skip.pdf"}}]}'
        ),
        encoding="utf-8",
    )

    settings_path = tmp_path / "config" / "settings.yaml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        "\n".join(
            [
                "llm:",
                "  provider: openai",
                "embedding:",
                "  provider: huggingface_local",
                "vector_store:",
                "  provider: chroma",
                "retrieval:",
                "  top_k: 5",
                "rerank:",
                "  provider: none",
                "evaluation:",
                "  provider: local",
                "observability:",
                f"  trace_file: {trace_file.as_posix()}",
                "  log_level: INFO",
                "dashboard:",
                "  traces_dir: logs",
                "  auto_refresh: true",
                "  refresh_interval: 5",
            ]
        ),
        encoding="utf-8",
    )

    service = TraceService(settings_path=settings_path)
    result = service.load_traces(trace_type="ingestion")

    assert len(result.records) == 1
    assert result.records[0].status == "skipped"
