"""Recall 回归测试（H5）。

这个测试覆盖的不是“某个单独函数算分对不对”，而是整条真实召回链路：
PDF -> Loader -> Chunker -> 本地确定性编码 -> Chroma/BM25 -> HybridSearch -> EvalRunner。

之所以把向量编码替换成本地确定性实现，而不是直接走线上 Embedding API，是因为：
- H5 的目标是“回归基线稳定”，不是测试外部模型服务可用性；
- 如果依赖真实网络和远端模型，测试结果会被网络抖动、供应商升级、配额问题污染；
- 但如果全部 mock 掉，又测不到真正的摄取/索引/检索闭环。

因此这里采用折中方案：
- 保留真实 Loader、Chunker、Chroma、BM25、HybridSearch、EvalRunner；
- 只把最不稳定的 Dense 编码改成本地可重复的假实现；
- Sparse 路径继续走真实 BM25 建索引与查询，从而让 H5 真正具备“回归守门”价值。
"""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("markitdown")
pytest.importorskip("fitz")
pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.hybrid_search import HybridSearch
from core.query_engine.dense_retriever import DenseRetriever
from core.query_engine.sparse_retriever import SparseRetriever
from core.settings import Settings, load_settings
from core.types import Chunk, ChunkRecord
from ingestion.chunking.document_chunker import DocumentChunker
from ingestion.embedding.batch_processor import BatchProcessor
from ingestion.pipeline import IngestionPipeline
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from ingestion.storage.vector_upserter import VectorUpserter
from ingestion.transform.chunk_refiner import ChunkRefiner
from ingestion.transform.image_captioner import ImageCaptioner
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.embedding.base_embedding import BaseEmbedding
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.loader.pdf_loader import PdfLoader
from libs.vector_store.chroma_store import ChromaStore
from observability.evaluation.eval_runner import EvalRunner
from libs.evaluator.custom_evaluator import CustomEvaluator

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents"
SIMPLE_PDF = FIXTURE_DIR / "simple.pdf"
COMPLEX_PDF = FIXTURE_DIR / "complex_technical_doc.pdf"


class _DeterministicEmbedding(BaseEmbedding):
    """本地确定性 embedding 假实现。

    做什么：
    - 把文本映射成固定长度向量；
    - 同一输入永远输出同一向量；
    - 不触网、不依赖模型文件。

    为什么：
    - DenseRetriever 需要真实走 `embedding -> vector_store.query` 契约；
    - 但 H5 关心的是“回归是否退化”，不关心外部模型是否恰好在线。

    关键权衡：
    - 这个向量不追求真实语义质量，只追求稳定和可区分；
    - 因此 H5 的阈值会设置成“最低可接受召回线”，而不是苛刻的生产指标。
    """

    def embed(self, texts: list[str], trace: Any | None = None) -> list[list[float]]:
        _ = trace
        vectors: list[list[float]] = []
        for text in texts:
            normalized = " ".join(str(text).lower().split())
            token_counts = Counter(token for token in normalized.split(" ") if token)
            vectors.append(
                [
                    float(len(normalized)),
                    float(token_counts.get("azure", 0)),
                    float(token_counts.get("openai", 0)),
                    float(token_counts.get("chunking", 0)),
                    float(token_counts.get("retrieval", 0)),
                    float(token_counts.get("hybrid", 0)),
                    float(token_counts.get("dense", 0)),
                    float(token_counts.get("sparse", 0)),
                    float(token_counts.get("vector", 0)),
                    float(token_counts.get("system", 0)),
                ]
            )
        return vectors


class _DeterministicBatchProcessor:
    """测试专用批处理器：同时产出稳定 dense 向量和真实 BM25 可消费的 sparse 词频。

    这里不直接复用生产 `BatchProcessor` 的原因是：
    - 生产版本内部会再去创建真实 DenseEncoder；
    - H5 要求不依赖外部 embedding API；
    - 但我们仍然保留 `ChunkRecord` 结构，确保下游 `VectorUpserter/BM25Indexer` 走真实逻辑。
    """

    def __init__(self, embedding: _DeterministicEmbedding) -> None:
        self._embedding = embedding

    def process(self, chunks: list[Chunk], trace: Any | None = None) -> list[ChunkRecord]:
        _ = trace
        dense_vectors = self._embedding.embed([chunk.text for chunk in chunks])
        records: list[ChunkRecord] = []

        for chunk, dense_vector in zip(chunks, dense_vectors):
            tokens = [token for token in chunk.text.lower().split() if token]
            sparse_vector = {term: float(freq) for term, freq in Counter(tokens).items()}
            if not sparse_vector:
                sparse_vector = {"__empty__": 1.0}

            records.append(
                ChunkRecord(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    dense_vector=dense_vector,
                    sparse_vector=sparse_vector,
                )
            )

        return records


@pytest.fixture()
def e2e_workspace() -> Path:
    """在项目目录内创建隔离工作区，保证 H5 不污染真实索引与历史数据。"""
    root = PROJECT_ROOT / ".pytest_tmp" / f"h5_recall_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _build_settings(workspace: Path) -> Settings:
    """构造 H5 专用 settings。

    设计目标：
    - 禁用需要真实 LLM/Vision 的 transform 增强，避免把 H5 变成网络集成测试；
    - 保留真实 Chroma/BM25 路径，但重定向到临时目录；
    - 关闭 rerank，把关注点锁定在 retrieval recall。
    """
    base = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))
    ingestion_cfg = replace(
        base.ingestion,
        batch_size=16,
        chunk_refiner=replace(base.ingestion.chunk_refiner, use_llm=False),
        metadata_enricher=replace(base.ingestion.metadata_enricher, use_llm=False),
    )
    evaluation_cfg = replace(
        base.evaluation,
        provider="custom",
        backends=("custom",),
    )
    return replace(
        base,
        vector_store=replace(base.vector_store, persist_dir=str(workspace / "data" / "db" / "chroma")),
        rerank=replace(base.rerank, enabled=False, provider="none"),
        vision_llm=replace(base.vision_llm, enabled=False),
        ingestion=ingestion_cfg,
        evaluation=evaluation_cfg,
        observability=replace(base.observability, trace_file=str(workspace / "logs" / "traces.jsonl")),
    )


def _build_pipeline(workspace: Path, settings: Settings, collection_name: str) -> IngestionPipeline:
    """组装 H5 使用的真实摄取链路。"""
    integrity_checker = SQLiteIntegrityChecker(db_path=str(workspace / "data" / "db" / "ingestion_history.db"))
    loader = PdfLoader(image_root=str(workspace / "loader_images"))
    chunker = DocumentChunker(settings=settings)
    image_storage = ImageStorage(
        image_root=str(workspace / "data" / "images"),
        db_path=str(workspace / "data" / "db" / "image_index.db"),
    )
    bm25_indexer = BM25Indexer(persist_dir=str(workspace / "data" / "db" / "bm25"))
    vector_store = ChromaStore(
        persist_dir=str(workspace / "data" / "db" / "chroma"),
        collection_name=collection_name,
    )
    vector_upserter = VectorUpserter(settings=settings, vector_store=vector_store)
    transforms = [
        ChunkRefiner(settings=settings),
        MetadataEnricher(settings=settings),
        ImageCaptioner(settings=settings),
    ]

    return IngestionPipeline(
        settings=settings,
        integrity_checker=integrity_checker,
        loader=loader,
        chunker=chunker,
        transforms=transforms,
        batch_processor=_DeterministicBatchProcessor(_DeterministicEmbedding()),
        bm25_indexer=bm25_indexer,
        vector_upserter=vector_upserter,
        image_storage=image_storage,
    )


def _build_hybrid_search(workspace: Path, settings: Settings, collection_name: str) -> HybridSearch:
    """构造与摄取阶段共用同一套底层索引的真实检索器。

    关键点：
    - DenseRetriever 必须连到“同一个 Chroma collection”；
    - SparseRetriever 必须连到“同一个 BM25 持久化目录”；
    - 否则测试虽然跑的是 `HybridSearch.search()`，但读到的却是另一套空索引。
    """
    vector_store = ChromaStore(
        persist_dir=str(workspace / "data" / "db" / "chroma"),
        collection_name=collection_name,
    )
    dense_retriever = DenseRetriever(
        settings=settings,
        embedding_client=_DeterministicEmbedding(),
        vector_store=vector_store,
    )
    sparse_retriever = SparseRetriever(
        settings=settings,
        bm25_indexer=BM25Indexer(persist_dir=str(workspace / "data" / "db" / "bm25")),
        vector_store=vector_store,
    )
    return HybridSearch(
        settings=settings,
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
    )


def _write_temp_golden_set(workspace: Path, collection: str) -> Path:
    """为 H5 生成隔离黄金集。

    为什么不直接改项目内 `tests/fixtures/golden_test_set.json`：
    - 该文件当前工作区已有未提交改动；
    - H5 不应该覆盖用户或其他任务正在调整的黄金集；
    - 用临时文件可以让测试完全自洽、可重复。
    """
    payload = {
        "test_cases": [
            {
                "query": "sample pdf document testing loader",
                "expected_sources": [str(SIMPLE_PDF.resolve())],
                "filters": {"collection": collection},
                "ground_truth": "The sample PDF explains loader testing and markdown conversion.",
            },
            {
                "query": "hybrid search dense sparse retrieval",
                "expected_sources": [str(COMPLEX_PDF.resolve())],
                "filters": {"collection": collection},
                "ground_truth": "The advanced RAG document introduces hybrid retrieval with dense and sparse search.",
            },
        ]
    }
    golden_path = workspace / "golden_test_set_h5.json"
    golden_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return golden_path


def _cleanup_collection(workspace: Path, collection_name: str) -> None:
    """删除本次测试使用的 Chroma collection，避免句柄残留。"""
    vector_store = ChromaStore(
        persist_dir=str(workspace / "data" / "db" / "chroma"),
        collection_name=collection_name,
    )
    vector_store._client.delete_collection(collection_name)


def test_recall_regression_hit_rate_meets_threshold(e2e_workspace: Path) -> None:
    """
    Given:
        一个隔离工作区、两份真实 PDF 样例，以及一套“真实摄取/真实检索/本地确定性 embedding”的回归环境。
        同时生成只属于本次测试的临时 golden test set，避免依赖共享 fixture 的外部改动。

    When:
        先通过 `IngestionPipeline.run()` 把 PDF 摄入到临时 Chroma/BM25，
        再用 `HybridSearch + EvalRunner + CustomEvaluator` 执行完整 recall 评估。

    Then:
        - 评估报告总用例数应与黄金集一致；
        - `hit_rate` 必须达到写死阈值，作为 H5 的回归基线；
        - 至少有一条样例命中 Top-1，防止测试退化成“勉强命中但排序全面变差”；
        - 所有 query 不应出现 retrieval 运行错误。
    """
    collection_name = f"h5_recall_{uuid.uuid4().hex[:8]}"
    business_collection = "h5_recall"
    settings = _build_settings(e2e_workspace)
    pipeline = _build_pipeline(e2e_workspace, settings, collection_name)
    golden_path = _write_temp_golden_set(e2e_workspace, business_collection)

    try:
        simple_result = pipeline.run(str(SIMPLE_PDF), collection=business_collection, force=True)
        complex_result = pipeline.run(str(COMPLEX_PDF), collection=business_collection, force=True)

        assert simple_result.skipped is False
        assert complex_result.skipped is False
        assert simple_result.chunk_count > 0
        assert complex_result.chunk_count > 0

        search = _build_hybrid_search(
            e2e_workspace,
            settings=settings,
            collection_name=collection_name,
        )

        runner = EvalRunner(
            settings=settings,
            hybrid_search=search,
            evaluator=CustomEvaluator(),
        )
        report = runner.run(str(golden_path))

        hit_threshold = 1.0
        top1_hit_minimum = 1

        assert report.total == 2
        assert report.hit_rate >= hit_threshold
        assert sum(1 for detail in report.details if detail.first_match_rank == 1) >= top1_hit_minimum
        assert all(detail.error is None for detail in report.details)
    finally:
        _cleanup_collection(e2e_workspace, collection_name)
