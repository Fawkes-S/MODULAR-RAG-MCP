"""QueryProcessor 单元测试（D1）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.query_processor import QueryProcessor  # noqa: E402
from core.settings import (  # noqa: E402
    EmbeddingSettings,
    EvaluationSettings,
    IngestionSettings,
    LLMSettings,
    ObservabilitySettings,
    RerankSettings,
    RetrievalSettings,
    Settings,
    VectorStoreSettings,
)


def _make_settings() -> Settings:
    return Settings(
        llm=LLMSettings(provider="openai", model="gpt-4o-mini"),
        embedding=EmbeddingSettings(provider="openai", model="text-embedding-3-small"),
        vector_store=VectorStoreSettings(provider="chroma", persist_dir="data/db/chroma"),
        retrieval=RetrievalSettings(top_k=8, sparse_top_k=20),
        rerank=RerankSettings(provider="none", enabled=False, top_m=30),
        evaluation=EvaluationSettings(provider="ragas", enabled=False),
        observability=ObservabilitySettings(log_level="INFO", trace_file="logs/traces.jsonl"),
        ingestion=IngestionSettings(),
    )


def test_query_processor_outputs_non_empty_keywords_and_dict_filters() -> None:
    """
    Given:
        一条正常的中英文混合查询，不额外传 filters 参数。
    When:
        调用 `QueryProcessor.process()` 执行预处理。
    Then:
        应返回非空 `keywords`，且 `filters` 必须是 dict，满足 D1 的最小契约。
    """
    processor = QueryProcessor(settings=_make_settings())

    result = processor.process("如何 配置 Azure OpenAI Embedding")

    assert result.keywords
    assert isinstance(result.filters, dict)


def test_query_processor_parses_inline_filters_and_excludes_them_from_keywords() -> None:
    """
    Given:
        query 中包含 `collection` 与 `doc_type` 的内联过滤表达式。
    When:
        执行查询预处理。
    Then:
        filters 中应提取到对应键值，关键词应来自真实检索语义，不包含过滤表达式本身。
    """
    processor = QueryProcessor(settings=_make_settings())

    result = processor.process("collection:manual doc_type=pdf 如何配置 Azure")

    assert result.filters == {"collection": "manual", "doc_type": "pdf"}
    assert "collection" not in result.keywords
    assert "doc_type" not in result.keywords
    assert "azure" in result.keywords


def test_query_processor_merges_external_filters_and_external_takes_precedence() -> None:
    """
    Given:
        query 内联 filters 与调用参数 `filters` 同时存在且有同名键。
    When:
        调用 `process(query, filters=...)`。
    Then:
        应完成合并，且外部传入值覆盖同名内联值，保证调用方拥有最终控制权。
    """
    processor = QueryProcessor(settings=_make_settings())

    result = processor.process(
        "collection:legacy source=guide.md Azure OpenAI",
        filters={"collection": "current", "language": "zh"},
    )

    assert result.filters == {"collection": "current", "source": "guide.md", "language": "zh"}


def test_query_processor_uses_fallback_when_all_tokens_are_stopwords() -> None:
    """
    Given:
        query 仅由停用词组成，正常关键词提取会得到空列表。
    When:
        执行预处理。
    Then:
        应触发回退逻辑并返回非空关键词，避免下游稀疏检索拿到空输入。
    """
    processor = QueryProcessor(settings=_make_settings())

    result = processor.process("the and 的 了")
    print("\n")
    print(result.keywords)

    assert result.keywords


def test_query_processor_rejects_invalid_query_input() -> None:
    """
    Given:
        非法 query 输入（空字符串与非字符串对象）。
    When:
        调用 `process()`。
    Then:
        应抛出 `ValueError`，阻止无效查询进入检索链路。
    """
    processor = QueryProcessor(settings=_make_settings())

    with pytest.raises(ValueError, match="query must be non-empty string"):
        processor.process("")
    with pytest.raises(ValueError, match="query must be non-empty string"):
        processor.process(123)  # type: ignore[arg-type]


def test_query_processor_rejects_non_dict_filters() -> None:
    """
    Given:
        `filters` 参数不是 dict。
    When:
        调用 `process()`。
    Then:
        应抛出 `ValueError`，确保过滤条件结构稳定为键值字典。
    """
    processor = QueryProcessor(settings=_make_settings())

    with pytest.raises(ValueError, match="filters must be dict"):
        processor.process("Azure OpenAI", filters=["bad"])  # type: ignore[arg-type]
