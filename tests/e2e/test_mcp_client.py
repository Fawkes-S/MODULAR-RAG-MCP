"""MCP Client 端到端测试（I1）。

这个文件验证的不是某个单独函数，而是“一个真实 MCP Client 站在外部”
时能不能把整条协议链路走通：

1. 先在隔离工作区里 ingest 一份真实 PDF；
2. 再以子进程方式启动真正的 MCP stdio server；
3. 依次发送 `initialize -> notifications/initialized -> tools/list -> tools/call`；
4. 最后确认 `query_knowledge_hub` 返回了 citations 和结构化结果。

为什么要这样测：
- 单元测试已经证明了各个模块自己能工作；
- I1 要补的是“模块串起来以后，Client 真正能不能用”；
- 因此这里必须同时覆盖协议、配置、索引加载和检索返回格式。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml

pytest.importorskip("chromadb")
pytest.importorskip("markitdown")
pytest.importorskip("fitz")
pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings
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

PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
SERVER_SCRIPT = PROJECT_ROOT / "src" / "mcp_server" / "server.py"
FIXTURE_PDF = PROJECT_ROOT / "tests" / "fixtures" / "sample_documents" / "complex_technical_doc.pdf"
QUERY_TEXT = "hybrid search dense sparse retrieval"
COLLECTION_NAME = "i1_e2e"


@pytest.fixture()
def mcp_workspace() -> Path:
    """在项目目录内创建 I1 专用隔离工作区。

    这样做的目的有两个：
    - 子进程 server 会把 `config/settings.yaml`、`data/db/*` 等相对路径都解析到这里；
    - 即使测试失败，也不会污染用户当前真实的 Chroma/BM25/trace 数据。
    """
    root = PROJECT_ROOT / ".pytest_tmp" / f"i1_mcp_client_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write_workspace_settings(workspace: Path) -> Path:
    """为 I1 生成一份隔离的 `config/settings.yaml`。

    关键设计：
    - 向量库、BM25、trace 都写到临时工作区；
    - 关闭 ChunkRefiner / MetadataEnricher / VisionCaption 的真实 LLM 路径，
      避免 I1 退化成外部模型联调测试；
    - Dense embedding 继续使用项目内本地模型，保证 server 查询走真实 dense route。
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
            "enabled": False,
            "backends": ["custom"],
            "golden_test_set": "tests/fixtures/golden_test_set.json",
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
    """组装与子进程 server 使用同一套存储路径的真实摄取链路。

    为什么这里不直接 `IngestionPipeline(settings)`：
    - 有些底层默认路径（例如 BM25）是相对路径；
    - 测试进程当前 cwd 是项目根目录，而子进程 server 的 cwd 会切到临时 workspace；
    - 如果这里不显式绑死路径，摄取和查询就可能读写两套不同索引，导致假失败。
    """
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


def _prepare_indexed_workspace(workspace: Path) -> tuple[Path, IngestionResult]:
    """在隔离工作区内完成真实 ingest，给 I1 server 查询准备数据。

    返回值同时带上 `settings_path` 和 `IngestionResult`，方便主测试断言：
    - ingest 确实成功了；
    - 后续 server 用的正是这份配置。
    """
    settings_path = _write_workspace_settings(workspace)
    settings = load_settings(str(settings_path))
    pipeline = _build_pipeline(settings=settings, workspace=workspace)
    result = pipeline.run(str(FIXTURE_PDF), collection=COLLECTION_NAME, force=True)
    return settings_path, result


def _run_mcp_session(workspace: Path, messages: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
    """以“客户端批量发送 JSON-RPC 消息”的方式运行一次 MCP 会话。

    这里故意不用内存版 `MCPServer(stdin=..., stdout=...)`，而是起真实子进程：
    - I1 验的是 Client 视角的端到端行为；
    - 所以必须把“stdio 通信、settings 相对路径解析、server 进程启动”都覆盖进去。
    """
    input_text = "\n".join(json.dumps(message, ensure_ascii=False) for message in messages) + "\n"
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_parts = [str(SRC_PATH)]
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    return subprocess.run(
        [str(PYTHON_EXE), str(SERVER_SCRIPT)],
        input=input_text,
        text=True,
        capture_output=True,
        timeout=180,
        cwd=str(workspace),
        env=env,
    )


def test_mcp_client_can_initialize_list_tools_and_call_query_tool_over_stdio(
    mcp_workspace: Path,
) -> None:
    """
    Given:
        一个隔离工作区，其中已经通过真实 `IngestionPipeline` 摄取了一份 PDF，
        并生成了 Chroma/BM25/trace 等查询所需数据。

    When:
        一个“模拟 MCP Client”以子进程方式启动真实 server，
        然后按协议顺序发送：
        1. `initialize`
        2. `notifications/initialized`
        3. `tools/list`
        4. `tools/call(query_knowledge_hub)`

    Then:
        - server 应成功返回 JSON-RPC 响应而不是崩溃；
        - `tools/list` 必须包含 `query_knowledge_hub`；
        - `tools/call` 必须返回非空结果和 citations；
        - citation 的来源文件应指向本次 ingest 的真实 PDF。
    """
    settings_path, ingest_result = _prepare_indexed_workspace(mcp_workspace)

    assert settings_path.exists()
    assert ingest_result.skipped is False
    assert ingest_result.chunk_count > 0
    assert ingest_result.vector_ids

    completed = _run_mcp_session(
        workspace=mcp_workspace,
        messages=[
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-mcp-client", "version": "0.0.1"},
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "query_knowledge_hub",
                    "arguments": {
                        "query": QUERY_TEXT,
                        "top_k": 3,
                        "collection": COLLECTION_NAME,
                    },
                },
            },
        ],
    )

    assert completed.returncode == 0, completed.stderr

    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    # `notifications/initialized` 是通知，不应产生响应，所以这里应该只有 3 条输出。
    assert len(output_lines) == 3, completed.stdout

    initialize_response = json.loads(output_lines[0])
    tools_list_response = json.loads(output_lines[1])
    tool_call_response = json.loads(output_lines[2])

    assert initialize_response["jsonrpc"] == "2.0"
    assert initialize_response["id"] == 1
    assert initialize_response["result"]["serverInfo"]["name"] == "modular-rag-mcp"

    tool_names = [tool["name"] for tool in tools_list_response["result"]["tools"]]
    assert "query_knowledge_hub" in tool_names

    query_tool_schema = next(
        tool for tool in tools_list_response["result"]["tools"] if tool["name"] == "query_knowledge_hub"
    )
    assert "query" in query_tool_schema["inputSchema"]["required"]

    structured = tool_call_response["result"]["structuredContent"]
    citations = structured["citations"]
    results = structured["results"]
    text_content = tool_call_response["result"]["content"][0]["text"]

    assert tool_call_response["jsonrpc"] == "2.0"
    assert tool_call_response["id"] == 3
    assert structured["query"] == QUERY_TEXT
    assert structured["result_count"] > 0
    assert citations
    assert results
    assert structured["collection"] == COLLECTION_NAME
    assert structured["fallback"] is False
    assert structured["trace_id"]
    assert "[1]" in text_content
    assert QUERY_TEXT in text_content

    first_citation = citations[0]
    assert first_citation["source"] == str(FIXTURE_PDF.resolve())
    assert first_citation["chunk_id"].startswith("chunk_")
    assert results[0]["metadata"]["collection"] == COLLECTION_NAME
