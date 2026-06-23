"""Dashboard 六页面冒烟测试（I2）。

这个文件验证的不是某个局部函数，而是：
1. 在一份隔离的真实工作区里先准备最小可用数据；
2. 再让 Dashboard 六个页面分别以真实 `Streamlit AppTest` 方式渲染；
3. 最后确认页面没有 Python 异常，并且至少渲染出各自的标题。

为什么不用“只测空页面”：
- `06-schedule.md` 对 I2 的要求是“页面在有数据时可正常渲染”；
- 如果只测空目录分支，很多页面虽然不会报错，但根本没有覆盖到真实
  `Settings / Chroma / BM25 / traces.jsonl / evaluation fixture` 的装配路径；
- 因此这里显式准备一份临时 ingest 数据，再补一条真实 query trace，
  让 G1-G6 页面的关键读取路径都至少跑一遍。
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest

pytest.importorskip("chromadb")
pytest.importorskip("markitdown")
pytest.importorskip("fitz")
pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.hybrid_search import HybridSearch
from core.query_engine.reranker import Reranker
from core.response.response_builder import ResponseBuilder
from core.settings import Settings, load_settings
from core.trace import TraceCollector
from ingestion.chunking.document_chunker import DocumentChunker
from ingestion.embedding.batch_processor import BatchProcessor
from ingestion.pipeline import IngestionPipeline, IngestionResult
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from ingestion.storage.vector_upserter import VectorUpserter
from ingestion.transform.chunk_refiner import ChunkRefiner
from ingestion.transform.image_captioner import ImageCaptioner
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.loader.pdf_loader import PdfLoader
from libs.vector_store.chroma_store import ChromaStore
from mcp_server.tools.query_knowledge_hub import QueryKnowledgeHubTool
from observability.dashboard.pages import (
    data_browser,
    evaluation_panel,
    ingestion_manager,
    ingestion_traces,
    overview,
    query_traces,
)

FIXTURE_PDF = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents" / "complex_technical_doc.pdf"
GOLDEN_TEST_SET = PROJECT_ROOT / "tests" / "fixtures" / "golden_test_set.json"
COLLECTION_NAME = "i2_dashboard"
QUERY_TEXT = "What is Modular RAG?"


@pytest.fixture(scope="module")
def dashboard_workspace() -> Path:
    """
    Given:
        需要一份不污染用户真实数据目录的隔离工作区。
    When:
        本测试准备 Chroma/BM25/image_index/traces/settings 等真实文件。
    Then:
        所有写操作都应落到 `.pytest_tmp/i2_dashboard_*` 下，测试结束后整体清理。
    """
    root = PROJECT_ROOT / ".pytest_tmp" / f"i2_dashboard_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="module")
def prepared_dashboard_settings_path(dashboard_workspace: Path) -> Path:
    """
    Given:
        六个 Dashboard 页面会共享同一份临时数据即可完成 I2 冒烟。
    When:
        先在模块级 fixture 中只准备一次 ingest/query/trace 数据。
    Then:
        参数化的 6 个页面用例可复用同一份工作区，避免重复 ingest 导致测试过慢。
    """
    original_cwd = Path.cwd()
    try:
        os.chdir(dashboard_workspace)
        return _prepare_workspace(dashboard_workspace)
    finally:
        os.chdir(original_cwd)


def _write_workspace_settings(workspace: Path) -> Path:
    """为 I2 生成隔离版 `config/settings.yaml`。

    做什么：
    - 把向量库、BM25、图片索引、trace 文件都定向到临时工作区；
    - 关闭需要真实外部 LLM 的 transform/rerank/evaluation 默认调用；
    - 保留本地 embedding 模型，让 Dashboard 读取到的是一份真实可查询索引。

    为什么：
    - I2 的目标是测试 Dashboard 页面装配与渲染，不是测试外部云服务；
    - 因此这里优先保证页面依赖的数据都真实存在，但成本和不稳定因素最小。
    """
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
        "embedding": {
            "provider": "huggingface_local",
            "model": str((PROJECT_ROOT / "data" / "models" / "all-MiniLM-L6-v2").resolve()),
            "device": "cpu",
            "batch_size": 16,
            "normalize_embeddings": False,
        },
        "vector_store": {
            "provider": "chroma",
            "persist_dir": str((workspace / "data" / "db" / "chroma").resolve()),
        },
        "retrieval": {
            "top_k": 5,
            "sparse_top_k": 10,
        },
        "rerank": {
            "enabled": False,
            "provider": "none",
            "top_m": 10,
            "timeout": 5.0,
        },
        "vision_llm": {
            "enabled": False,
        },
        "evaluation": {
            "provider": "custom",
            "enabled": True,
            "backends": ["custom"],
            "golden_test_set": str(GOLDEN_TEST_SET.resolve()),
        },
        "observability": {
            "log_level": "INFO",
            "trace_file": str((workspace / "logs" / "traces.jsonl").resolve()),
        },
        "dashboard": {
            "enabled": True,
            "port": 8501,
            "traces_dir": str((workspace / "logs").resolve()),
            "auto_refresh": False,
            "refresh_interval": 5,
        },
        "ingestion": {
            "splitter": "recursive",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "batch_size": 16,
            "chunk_refiner": {
                "use_llm": False,
            },
            "metadata_enricher": {
                "use_llm": False,
            },
        },
    }

    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return settings_path


def _build_pipeline(settings: Settings, workspace: Path) -> IngestionPipeline:
    """组装与 Dashboard 读取同一路径的真实 ingestion 链路。"""
    vector_store = ChromaStore(
        persist_dir=str((workspace / "data" / "db" / "chroma").resolve()),
        collection_name="chunks",
    )
    return IngestionPipeline(
        settings=settings,
        integrity_checker=SQLiteIntegrityChecker(
            db_path=str((workspace / "data" / "db" / "ingestion_history.db").resolve())
        ),
        loader=PdfLoader(image_root=str((workspace / "loader_images").resolve())),
        chunker=DocumentChunker(settings=settings),
        transforms=[
            ChunkRefiner(settings=settings),
            MetadataEnricher(settings=settings),
            ImageCaptioner(settings=settings),
        ],
        batch_processor=BatchProcessor(settings=settings),
        bm25_indexer=BM25Indexer(
            persist_dir=str((workspace / "data" / "db" / "bm25").resolve())
        ),
        vector_upserter=VectorUpserter(settings=settings, vector_store=vector_store),
        image_storage=ImageStorage(
            image_root=str((workspace / "data" / "images").resolve()),
            db_path=str((workspace / "data" / "db" / "image_index.db").resolve()),
        ),
    )


def _prepare_query_trace(settings: Settings, settings_path: Path) -> dict[str, object]:
    """执行一次真实 query，确保 G6 页面不是只走“空 trace”分支。

    做什么：
    - 复用项目当前 QueryKnowledgeHubTool 真正跑一遍查询；
    - 让工具内部按项目正式路径写出 `query` trace；
    - 返回结构化结果，给测试顺手做一层前置校验。

    为什么：
    - Query Trace 页面依赖的不是向量库本身，而是 `logs/traces.jsonl` 中的 `query` 记录；
    - 只做 ingest 只能生成 `ingestion` trace，不足以覆盖 G6 的主分支。
    """
    hybrid_search = HybridSearch(settings=settings)
    reranker = Reranker(settings=settings)
    response_builder = ResponseBuilder()
    tool = QueryKnowledgeHubTool(
        settings_path=str(settings_path),
        settings_loader=lambda _path: settings,
        searcher=hybrid_search,
        reranker=reranker,
        response_builder=response_builder,
        trace_collector=TraceCollector(trace_file=settings.observability.trace_file),
    )
    result = tool.handle({"query": QUERY_TEXT, "top_k": 3, "collection": COLLECTION_NAME})
    assert result["structuredContent"]["result_count"] > 0
    return result


def _prepare_workspace(workspace: Path) -> Path:
    """在隔离工作区准备 I2 冒烟所需的最小真实数据。"""
    settings_path = _write_workspace_settings(workspace)
    settings = load_settings(str(settings_path))
    pipeline = _build_pipeline(settings=settings, workspace=workspace)
    ingest_result: IngestionResult = pipeline.run(str(FIXTURE_PDF), collection=COLLECTION_NAME, force=True)

    # 这里先验证 ingest 真实成功，再补一条 query trace。
    assert ingest_result.skipped is False
    assert ingest_result.chunk_count > 0
    assert ingest_result.vector_ids

    query_result = _prepare_query_trace(settings, settings_path)
    citations = query_result["structuredContent"]["citations"]
    assert citations

    trace_file = Path(settings.observability.trace_file)
    assert trace_file.exists()
    raw_lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(line.get("trace_type") == "ingestion" for line in raw_lines)
    assert any(line.get("trace_type") == "query" for line in raw_lines)
    return settings_path


def _run_page_smoke(
    *,
    title_text: str,
    page_key: str,
    settings_path: Path,
) -> None:
    """用真实 `AppTest` 跑单页冒烟并断言“无异常 + 有标题”。

    为什么逐页测试：
    - Streamlit 多页面导航在测试环境里切页控制不如直接调用 `render()` 稳定；
    - I2 的验收点本质是“6 个页面都能加载、不会抛 Python 异常”；
    - 因此这里把每页当成一个最小 app 来跑，稳定性更高，也更利于精确定位失败页。
    """

    script = f"""
from pathlib import Path
import sys

SRC_PATH = Path(r"{SRC_PATH}")
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.vector_store.chroma_store import ChromaStore
from observability.dashboard.pages import overview, data_browser, ingestion_manager, ingestion_traces, query_traces, evaluation_panel
from observability.dashboard.pages.ingestion_manager import IngestionManagerService
from observability.dashboard.pages.evaluation_panel import EvaluationPanelService
from observability.dashboard.services.config_service import ConfigService
from observability.dashboard.services.data_service import DataService
from observability.dashboard.services.trace_service import TraceService

settings_path = Path(r"{settings_path}")
page_key = {page_key!r}

if page_key == "overview":
    config_service = ConfigService(settings_path=settings_path)
    settings = config_service.load_settings()
    vector_store = ChromaStore(persist_dir=settings.vector_store.persist_dir)
    overview.render(config_service=config_service, vector_store=vector_store)
elif page_key == "data_browser":
    data_browser.render(data_service=DataService(settings_path=settings_path))
elif page_key == "ingestion_manager":
    ingestion_manager.render(manager_service=IngestionManagerService(settings_path=settings_path))
elif page_key == "ingestion_traces":
    ingestion_traces.render(trace_service=TraceService(settings_path=settings_path))
elif page_key == "query_traces":
    query_traces.render(trace_service=TraceService(settings_path=settings_path))
elif page_key == "evaluation_panel":
    evaluation_panel.render(evaluation_service=EvaluationPanelService(settings_path=settings_path))
else:
    raise RuntimeError(f"unknown page key: {{page_key}}")
"""

    app_test = AppTest.from_string(script, default_timeout=120)
    app_test.run(timeout=120)

    # 关键断言 1：页面执行过程中不能出现 Python 异常。
    assert len(app_test.exception) == 0, [item.value for item in app_test.exception]

    # 关键断言 2：页面至少渲染出自己的标题，证明不是提前中断。
    rendered_titles = [item.value for item in app_test.title]
    assert title_text in rendered_titles
@pytest.mark.parametrize(
    ("title_text", "page_key"),
    [
        (
            "系统总览",
            "overview",
        ),
        (
            "数据浏览器",
            "data_browser",
        ),
        (
            "Ingestion 管理",
            "ingestion_manager",
        ),
        (
            "Ingestion 追踪",
            "ingestion_traces",
        ),
        (
            "Query 追踪",
            "query_traces",
        ),
        (
            "评估面板",
            "evaluation_panel",
        ),
    ],
)
def test_dashboard_pages_render_without_python_exceptions_with_real_workspace_data(
    dashboard_workspace: Path,
    prepared_dashboard_settings_path: Path,
    title_text: str,
    page_key: str,
) -> None:
    """
    Given:
        一份隔离工作区中已经完成真实 ingest，且写出了 ingestion/query traces。
    When:
        使用 Streamlit `AppTest` 分别渲染 Dashboard 六个页面。
    Then:
        - 每个页面都不应出现 Python 异常；
        - 每个页面都应渲染出自己的标题；
        - 这证明 Dashboard 在“有真实数据”时具备最小可用加载能力。
    """
    original_cwd = Path.cwd()
    settings_path = prepared_dashboard_settings_path

    try:
        # 很多 Dashboard service 通过相对路径解析项目资源，因此这里显式切到临时工作区，
        # 让“settings 所在项目根目录”与“当前运行上下文”保持一致，避免读取到用户真实数据。
        os.chdir(dashboard_workspace)
        _run_page_smoke(
            title_text=title_text,
            page_key=page_key,
            settings_path=settings_path,
        )
    finally:
        os.chdir(original_cwd)
