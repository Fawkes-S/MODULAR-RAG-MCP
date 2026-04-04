"""真实链路摄取调试脚本。

用途：
- 复用 `config/settings.yaml` 的真实配置执行 ingestion；
- 对每个文件输出阶段级 trace（pipeline + transform）；
- 将关键调试信息（LLM/Vision 成功数、回退原因）直接打印出来，
  用于排查“为什么走了 rule fallback”。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings
from core.trace.trace_context import TraceContext
from ingestion.pipeline import IngestionPipeline


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数。"""
    parser = argparse.ArgumentParser(
        description="运行真实 ingestion 并输出详细 trace，便于排查 LLM/Vision 回退。"
    )
    parser.add_argument("--path", required=True, help="PDF 文件路径，或包含 PDF 的目录。")
    parser.add_argument("--collection", default="real_debug", help="目标 collection（默认: real_debug）。")
    parser.add_argument("--force", action="store_true", help="忽略增量命中，强制重处理。")
    parser.add_argument(
        "--settings",
        default=str(PROJECT_ROOT / "config" / "settings.yaml"),
        help="settings.yaml 路径（默认: config/settings.yaml）。",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="最多处理多少个文件（0 表示不限制，便于快速调试）。",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="可选：将完整执行结果写入 JSON 文件（含每个 stage 的 details）。",
    )
    return parser


def _resolve_input_files(path_value: str) -> list[str]:
    """把输入路径解析为稳定有序的 PDF 文件列表。

    做什么：
    - 支持单文件模式与目录递归模式；
    - 目录模式下仅收集 `*.pdf`，并排序确保执行顺序可复现。

    为什么：
    - 调试脚本最重要的是“同样输入可以稳定复现同样问题”；
    - 顺序稳定后，日志与 JSON 结果才便于 diff。

    失败路径：
    - 路径不存在：`FileNotFoundError`
    - 文件模式但不是 PDF：`ValueError`
    - 目录下无 PDF：`FileNotFoundError`
    """
    target = Path(path_value).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Input path not found: {target}")

    if target.is_file():
        if target.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF file is supported for --path file mode: {target}")
        return [str(target)]

    pdf_files = sorted(file.resolve() for file in target.rglob("*.pdf") if file.is_file())
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found under directory: {target}")
    return [str(path) for path in pdf_files]


def _build_pipeline(settings: Settings) -> IngestionPipeline:
    """构建真实 IngestionPipeline（不注入 fake 组件）。"""
    return IngestionPipeline(settings=settings)


def _compact_details(details: dict[str, Any], max_len: int = 240) -> str:
    """把 stage details 压缩成单行，避免控制台被超长 JSON 淹没。"""
    text = json.dumps(details, ensure_ascii=False, sort_keys=True)
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."


def _print_runtime_snapshot(settings: Settings, collection: str) -> None:
    """输出当前关键配置快照，帮助确认“到底在用哪套真实配置”。"""
    print("[CONFIG] effective runtime snapshot")
    print(
        f"  llm: provider={settings.llm.provider} model={settings.llm.model} "
        f"timeout={settings.llm.timeout}s retries={settings.llm.max_retries}"
    )
    print(
        f"  vision: enabled={settings.vision_llm.enabled} provider={settings.vision_llm.provider} "
        f"model={settings.vision_llm.model} timeout={settings.vision_llm.timeout}s "
        f"retries={settings.vision_llm.max_retries}"
    )
    print(
        f"  embedding: provider={settings.embedding.provider} model={settings.embedding.model} "
        f"device={settings.embedding.device} batch_size={settings.embedding.batch_size}"
    )
    print(
        "  transform_flags: "
        f"chunk_refiner.use_llm={settings.ingestion.chunk_refiner.use_llm} "
        f"metadata_enricher.use_llm={settings.ingestion.metadata_enricher.use_llm}"
    )
    print(
        f"  storage: vector_store.persist_dir={settings.vector_store.persist_dir} "
        f"collection={collection}"
    )


def _print_trace(trace: TraceContext) -> None:
    """打印阶段级追踪。

    做什么：
    - 按记录顺序输出所有 stage；
    - 同时关注两类阶段：
      1) `pipeline.*`（编排层）
      2) `transform.*`（能力层）

    为什么：
    - 仅看最终成功/失败无法定位问题发生在哪一层；
    - 该输出可直接对应到 pipeline/transform 的实现位置。
    """
    print(f"[TRACE] trace_id={trace.trace_id} stage_count={len(trace.stages)}")
    for idx, stage in enumerate(trace.stages, start=1):
        stage_name = str(stage.get("stage_name", ""))
        status = str(stage.get("status", ""))
        elapsed_ms = stage.get("elapsed_ms")
        details = stage.get("details") if isinstance(stage.get("details"), dict) else {}

        elapsed_text = f"{float(elapsed_ms):.2f}ms" if elapsed_ms is not None else "-"
        print(
            f"  [{idx:02d}] name={stage_name} status={status} elapsed={elapsed_text} "
            f"details={_compact_details(details)}"
        )


def _extract_transform_focus(trace: TraceContext) -> list[str]:
    """提炼 transform 关键观测项，帮助快速判断是否走到 LLM/Vision 成功路径。"""
    focus_lines: list[str] = []
    focus_stage_names = [
        "transform.chunk_refiner",
        "transform.metadata_enricher",
        "transform.image_captioner",
    ]

    stage_map = {str(stage.get("stage_name")): stage for stage in trace.stages}
    for name in focus_stage_names:
        stage = stage_map.get(name)
        if stage is None:
            focus_lines.append(f"{name}: <missing>")
            continue

        details = stage.get("details") if isinstance(stage.get("details"), dict) else {}
        if name == "transform.chunk_refiner":
            focus_lines.append(
                f"{name}: total={details.get('total')} llm_success={details.get('llm_success')} "
                f"rule_fallback={details.get('rule_fallback')} errors={details.get('errors')}"
            )
        elif name == "transform.metadata_enricher":
            focus_lines.append(
                f"{name}: total={details.get('total')} llm_success={details.get('llm_success')} "
                f"rule_fallback={details.get('rule_fallback')} errors={details.get('errors')}"
            )
        else:
            focus_lines.append(
                f"{name}: chunks_with_images={details.get('chunks_with_images')} "
                f"captioned_images={details.get('captioned_images')} "
                f"fallback_images={details.get('fallback_images')} "
                f"errors={details.get('errors')}"
            )

    return focus_lines


def main(argv: list[str] | None = None) -> int:
    """调试主流程：加载配置 -> 构建 pipeline -> 执行并打印可排障结果。"""
    args = _build_parser().parse_args(argv)

    settings_path = Path(args.settings).resolve()
    settings = load_settings(str(settings_path))
    files = _resolve_input_files(args.path)

    max_files = int(args.max_files)
    if max_files > 0:
        files = files[:max_files]

    pipeline = _build_pipeline(settings)

    print(
        f"[REAL_DEBUG] start at={datetime.now().isoformat()} settings={settings_path} "
        f"total_files={len(files)} collection={args.collection} force={bool(args.force)}"
    )
    _print_runtime_snapshot(settings, collection=args.collection)

    reports: list[dict[str, Any]] = []
    failed_count = 0

    for index, source_path in enumerate(files, start=1):
        print("\n" + "=" * 88)
        print(f"[FILE] {index}/{len(files)} source={source_path}")

        trace = TraceContext(trace_type="ingestion")
        try:
            result = pipeline.run(
                source_path=source_path,
                collection=args.collection,
                force=bool(args.force),
                trace=trace,
            )

            print(
                f"[RESULT] skipped={result.skipped} chunks={result.chunk_count} "
                f"vectors={len(result.vector_ids)} images={result.image_count} bm25_terms={result.bm25_terms}"
            )
            _print_trace(trace)
            print("[FOCUS]")
            for line in _extract_transform_focus(trace):
                print(f"  - {line}")

            reports.append(
                {
                    "source_path": source_path,
                    "status": "ok",
                    "result": {
                        "skipped": result.skipped,
                        "file_hash": result.file_hash,
                        "chunk_count": result.chunk_count,
                        "vector_count": len(result.vector_ids),
                        "image_count": result.image_count,
                        "bm25_terms": result.bm25_terms,
                        "trace_id": result.trace_id,
                    },
                    "trace": trace.to_dict(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            print(f"[ERROR] {type(exc).__name__}: {exc}")
            _print_trace(trace)
            print("[FOCUS]")
            for line in _extract_transform_focus(trace):
                print(f"  - {line}")

            reports.append(
                {
                    "source_path": source_path,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "trace": trace.to_dict(),
                }
            )

    if args.json_out:
        out_path = Path(args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REAL_DEBUG] json report written: {out_path}")

    success_count = len(files) - failed_count
    print(
        f"[REAL_DEBUG] done total={len(files)} success={success_count} "
        f"failed={failed_count} exit_code={(0 if failed_count == 0 else 1)}"
    )
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())


'''
单文件调试:
.\.venv\Scripts\python.exe scripts\ingest_real_debug.py `
  --path tests\fixtures\sample_documents\complex_technical_doc.pdf `
  --collection real_debug_tmp_complex `
  --force `
  --json-out .pytest_tmp\ingest_real_debug_report_complex.json

目录批量调试（只跑前2个文件）
.\.venv\Scripts\python.exe scripts\ingest_real_debug.py `
  --path tests\fixtures\sample_documents `
  --collection real_debug_batch `
  --force `
  --max-files 2 `
  --json-out .pytest_tmp\ingest_real_debug_batch.json

'''
