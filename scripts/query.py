"""在线查询脚本入口（D7）。

提供命令行参数：
- `--query`：查询文本（必填）；
- `--top-k`：返回条数（默认 10）；
- `--collection`：可选集合过滤；
- `--verbose`：显示 Dense/Sparse/Fusion/Rerank 中间结果；
- `--no-rerank`：跳过 Reranker 阶段，直接输出 HybridSearch 结果。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.dense_retriever import DenseRetriever
from core.query_engine.fusion import RRFFusion
from core.query_engine.hybrid_search import HybridSearch
from core.query_engine.query_processor import QueryProcessor
from core.query_engine.reranker import Reranker, RerankOutput
from core.query_engine.sparse_retriever import SparseRetriever
from core.settings import Settings, load_settings
from core.trace.trace_context import TraceContext
from core.types import RetrievalResult
from observability.logger import get_logger

LOGGER = get_logger("scripts.query")


def _build_parser() -> argparse.ArgumentParser:
    """构建 query 命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="在线查询知识库（HybridSearch + 可选 Reranker）。")
    parser.add_argument("--query", required=True, help="查询文本（必填）。")
    parser.add_argument("--top-k", type=int, default=10, help="返回结果数量（默认: 10）。")
    parser.add_argument("--collection", default="", help="限定检索集合（可选）。")
    parser.add_argument("--verbose", action="store_true", help="显示 Dense/Sparse/Fusion/Rerank 中间结果。")
    parser.add_argument("--no-rerank", action="store_true", help="跳过 Reranker 阶段，直接输出 Fusion 结果。")
    return parser


def _normalize_top_k(top_k: int) -> int:
    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be positive int")
    return top_k


def _build_components(settings: Settings, *, create_reranker: bool) -> dict[str, Any]:
    """构建查询链路组件。

    单独封装用于保持脚本主流程清晰，也方便后续测试注入替身。
    """
    query_processor = QueryProcessor(settings=settings)
    dense_retriever = DenseRetriever(settings=settings)
    sparse_retriever = SparseRetriever(settings=settings)
    fusion = RRFFusion()
    hybrid_search = HybridSearch(
        settings=settings,
        query_processor=query_processor,
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        fusion=fusion,
    )
    components: dict[str, Any] = {
        "query_processor": query_processor,
        "dense_retriever": dense_retriever,
        "sparse_retriever": sparse_retriever,
        "fusion": fusion,
        "hybrid_search": hybrid_search,
    }
    if create_reranker:
        components["reranker"] = Reranker(settings=settings)
    return components


def _format_snippet(text: str, limit: int = 120) -> str:
    """格式化展示摘要，避免命令行输出过长。"""
    flat = " ".join(str(text).split())
    if len(flat) <= limit:
        return flat
    return f"{flat[:limit]}..."


def _print_result_block(title: str, results: list[RetrievalResult], limit: int) -> None:
    """打印结果列表（用于默认输出与 verbose 中间输出）。"""
    print(f"\n[{title}] count={len(results)}")
    if not results:
        print("  (empty)")
        return

    for index, item in enumerate(results[:limit], start=1):
        source = str(item.metadata.get("source_path", "-"))
        page = item.metadata.get("page", "-")
        print(
            f"  {index}. id={item.chunk_id} score={item.score:.4f} source={source} page={page}\n"
            f"     text={_format_snippet(item.text)}"
        )


def _print_final_results(results: list[RetrievalResult], top_k: int) -> None:
    """打印默认 Top-K 输出。"""
    print(f"\n[QUERY] Top-{top_k} results")
    _print_result_block("final", results, limit=top_k)


def _run_verbose_pipeline(
    *,
    settings: Settings,
    query_text: str,
    top_k: int,
    filters: dict[str, Any],
    query_processor: QueryProcessor,
    dense_retriever: DenseRetriever,
    sparse_retriever: SparseRetriever,
    fusion: RRFFusion,
    reranker: Reranker | None,
    disable_rerank: bool,
) -> None:
    """在 verbose 模式下打印各阶段中间结果。

    这里仅用于调试可视化；最终候选仍以 `HybridSearch.search()` 主链路结果为准。
    """
    processed = query_processor.process(query=query_text, filters=filters)
    dense_k = max(top_k, int(settings.retrieval.top_k))
    sparse_k = max(top_k, int(settings.retrieval.sparse_top_k))

    dense_results: list[RetrievalResult]
    sparse_results: list[RetrievalResult]
    dense_error: str | None = None
    sparse_error: str | None = None

    try:
        dense_results = dense_retriever.retrieve(
            query=processed.normalized_query,
            top_k=dense_k,
            filters=processed.filters,
        )
    except Exception as exc:  # noqa: BLE001
        dense_results = []
        dense_error = f"{type(exc).__name__}: {exc}"

    try:
        sparse_results = sparse_retriever.retrieve(
            keywords=processed.keywords,
            top_k=sparse_k,
        )
    except Exception as exc:  # noqa: BLE001
        sparse_results = []
        sparse_error = f"{type(exc).__name__}: {exc}"

    if dense_error:
        print(f"\n[verbose] dense_error={dense_error}")
    if sparse_error:
        print(f"\n[verbose] sparse_error={sparse_error}")

    _print_result_block("dense", dense_results, limit=top_k)
    _print_result_block("sparse", sparse_results, limit=top_k)

    fusion_k = max(dense_k, sparse_k)
    fusion_results = fusion.fuse(
        dense_results=dense_results,
        sparse_results=sparse_results,
        top_k=fusion_k,
    )
    filtered_fusion = HybridSearch._apply_metadata_filters(fusion_results, processed.filters)[:top_k]
    _print_result_block("fusion", filtered_fusion, limit=top_k)

    if disable_rerank:
        print("\n[verbose] rerank skipped by --no-rerank")
        return

    if reranker is None:
        print("\n[verbose] rerank unavailable (not initialized)")
        return

    rerank_output = reranker.rerank(
        query=processed.normalized_query,
        candidates=filtered_fusion,
        top_k=top_k,
    )
    _print_result_block("rerank", rerank_output.results, limit=top_k)
    print(
        f"[verbose] rerank backend={rerank_output.backend} "
        f"fallback={rerank_output.fallback} "
        f"reason={rerank_output.fallback_reason}"
    )


def _handle_empty_or_unavailable(error: Exception | None = None) -> int:
    """统一输出无数据/不可检索时的友好提示。"""
    if error is not None:
        LOGGER.warning("Query fallback to friendly empty message: %s: %s", type(error).__name__, error)
    print("未找到相关文档，请先运行 ingest.py 摄取数据。")
    return 0


def main(argv: list[str] | None = None) -> int:
    """脚本主流程：参数解析 -> HybridSearch -> 可选 Rerank -> 输出结果。"""
    args = _build_parser().parse_args(argv)
    top_k = _normalize_top_k(args.top_k)

    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    should_create_reranker = (not bool(args.no_rerank)) or bool(args.verbose)
    components = _build_components(settings, create_reranker=should_create_reranker)

    query_processor: QueryProcessor = components["query_processor"]
    dense_retriever: DenseRetriever = components["dense_retriever"]
    sparse_retriever: SparseRetriever = components["sparse_retriever"]
    fusion: RRFFusion = components["fusion"]
    hybrid_search: HybridSearch = components["hybrid_search"]
    reranker: Reranker | None = components.get("reranker")

    filters: dict[str, Any] = {}
    if str(args.collection).strip():
        filters["collection"] = str(args.collection).strip()

    trace = TraceContext(trace_type="query")

    print(
        f"[QUERY] start top_k={top_k} collection={filters.get('collection', '<any>')} "
        f"rerank={'off' if args.no_rerank else 'on'} verbose={bool(args.verbose)}"
    )

    if args.verbose:
        _run_verbose_pipeline(
            settings=settings,
            query_text=args.query,
            top_k=top_k,
            filters=filters,
            query_processor=query_processor,
            dense_retriever=dense_retriever,
            sparse_retriever=sparse_retriever,
            fusion=fusion,
            reranker=reranker,
            disable_rerank=bool(args.no_rerank),
        )

    try:
        hybrid_results = hybrid_search.search(
            query=args.query,
            top_k=top_k,
            filters=filters or None,
            trace=trace,
        )
    except RuntimeError as exc:
        # 无索引或双路不可用时返回友好提示，而不是让 CLI 直接失败退出。
        return _handle_empty_or_unavailable(error=exc)

    if not hybrid_results:
        return _handle_empty_or_unavailable()

    if args.no_rerank:
        final_output = RerankOutput(
            results=hybrid_results,
            fallback=False,
            fallback_reason=None,
            backend="disabled_by_flag",
        )
    else:
        if reranker is None:
            raise RuntimeError("reranker not initialized while --no-rerank is false")
        final_output = reranker.rerank(
            query=args.query,
            candidates=hybrid_results,
            top_k=top_k,
            trace=trace,
        )

    if not final_output.results:
        return _handle_empty_or_unavailable()

    _print_final_results(final_output.results, top_k=top_k)
    print(
        f"\n[QUERY] done backend={final_output.backend} "
        f"fallback={final_output.fallback} "
        f"fallback_reason={final_output.fallback_reason}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Query command failed: %s", exc)
        raise SystemExit(1) from exc
