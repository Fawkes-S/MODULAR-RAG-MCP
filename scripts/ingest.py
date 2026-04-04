"""离线摄取脚本入口（C15）。

提供命令行参数：
- `--path`：单个 PDF 文件或包含 PDF 的目录；
- `--collection`：目标集合名；
- `--force`：忽略增量跳过，强制重建。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings
from ingestion.pipeline import IngestionPipeline, IngestionResult
from observability.logger import get_logger

LOGGER = get_logger("scripts.ingest")


def _build_parser() -> argparse.ArgumentParser:
    """构建 ingest 命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="离线摄取 PDF 到向量库与 BM25 索引。")
    parser.add_argument("--path", required=True, help="PDF 文件路径，或包含 PDF 的目录路径。")
    parser.add_argument("--collection", default="default", help="目标集合名（默认: default）。")
    parser.add_argument("--force", action="store_true", help="忽略增量跳过，强制重处理。")
    return parser


def _resolve_input_files(path_value: str) -> list[str]:
    """把 `--path` 解析为稳定有序的 PDF 文件列表。

    做什么：
    - 支持“单个 PDF 文件”与“目录批量摄取”两种入口；
    - 目录模式下递归收集 `*.pdf`，并按路径排序保证执行顺序稳定。

    为什么：
    - C15 既要求离线脚本入口可用，也要求兼容后续批处理与 E2E 验收命令。

    关键约束：
    - 仅接受 PDF；避免把 txt/json 等不受支持类型交给 `PdfLoader` 导致后置失败。

    失败路径：
    - 路径不存在：抛 `FileNotFoundError`；
    - 输入是文件但不是 PDF：抛 `ValueError`；
    - 目录下没有 PDF：抛 `FileNotFoundError`。
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
    return [str(file) for file in pdf_files]


def _build_pipeline(settings: Settings) -> IngestionPipeline:
    """构建默认 IngestionPipeline。

    单独封装工厂函数是为了让测试可通过 monkeypatch 注入 fake pipeline，
    只验证脚本编排行为，不耦合外部模型或向量库依赖。
    """
    return IngestionPipeline(settings=settings)


def _run_single_file(
    pipeline: IngestionPipeline,
    *,
    source_path: str,
    collection: str,
    force: bool,
) -> IngestionResult:
    """执行单文件摄取并返回结果。"""
    return pipeline.run(source_path=source_path, collection=collection, force=force)


def main(argv: list[str] | None = None) -> int:
    """脚本主流程：参数解析 -> 构建 pipeline -> 执行摄取 -> 返回退出码。"""
    args = _build_parser().parse_args(argv)

    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    source_files = _resolve_input_files(args.path)
    pipeline = _build_pipeline(settings)

    print(
        f"[INGEST] start total={len(source_files)} collection={args.collection} force={bool(args.force)}"
    )

    failed_count = 0
    for index, source_path in enumerate(source_files, start=1):
        try:
            result = _run_single_file(
                pipeline,
                source_path=source_path,
                collection=args.collection,
                force=bool(args.force),
            )

            if result.skipped:
                print(f"[{index}/{len(source_files)}][SKIP] {source_path} file_hash={result.file_hash}")
                continue

            print(
                f"[{index}/{len(source_files)}][OK] {source_path} "
                f"chunks={result.chunk_count} vectors={len(result.vector_ids)} "
                f"images={result.image_count} bm25_terms={result.bm25_terms}"
            )
        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            LOGGER.exception("Failed to ingest %s: %s", source_path, exc)
            print(f"[{index}/{len(source_files)}][FAIL] {source_path} error={type(exc).__name__}: {exc}")

    success_count = len(source_files) - failed_count
    print(
        f"[INGEST] done total={len(source_files)} success={success_count} failed={failed_count}"
    )
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Ingest command failed: %s", exc)
        raise SystemExit(1) from exc
