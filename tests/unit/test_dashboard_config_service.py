"""Dashboard 配置服务与总览快照测试。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard.pages.overview import build_overview_snapshot
from observability.dashboard.services.config_service import ConfigService


class _FakeVectorStore:
    """测试用假向量库，仅返回固定统计结果。"""

    def get_collection_stats(self) -> dict[str, object]:
        return {
            "collection_name": "chunks",
            "chunk_count": 12,
            "document_count": 3,
            "image_count": 2,
            "collections": [
                {"name": "manual", "chunk_count": 12, "document_count": 3, "image_count": 2},
            ],
        }


def test_config_service_formats_component_cards_from_project_settings() -> None:
    """
    Given:
        当前项目真实的 `config/settings.yaml`，其中包含 llm/embedding/rerank/dashboard 等配置。

    When:
        调用 `ConfigService.build_component_cards()` 生成 Overview 组件卡片。

    Then:
        - 返回 5 张核心组件卡片；
        - 卡片标题覆盖 LLM/Embedding/Splitter/Reranker/Evaluator；
        - 每张卡片都包含可直接展示的摘要文本。
    """
    service = ConfigService(PROJECT_ROOT / "config" / "settings.yaml")

    cards = service.build_component_cards()

    assert [card.title for card in cards] == ["LLM", "Embedding", "Splitter", "Reranker", "Evaluator"]
    assert all(card.summary for card in cards)
    assert any("chunk_size" in detail for detail in cards[2].details)


def test_build_overview_snapshot_combines_config_and_collection_stats() -> None:
    """
    Given:
        真实配置服务与一个返回固定统计值的假向量库。

    When:
        调用 `build_overview_snapshot()` 聚合 Overview 页面所需数据。

    Then:
        - 组件卡片来自配置服务；
        - collection 统计来自向量库；
        - Dashboard 运行状态中能读到端口与 trace 文件信息；
        - 整个快照不应出现统计错误。
    """
    service = ConfigService(PROJECT_ROOT / "config" / "settings.yaml")

    snapshot = build_overview_snapshot(config_service=service, vector_store=_FakeVectorStore())

    assert len(snapshot.component_cards) == 5
    assert snapshot.collection_stats["chunk_count"] == 12
    assert snapshot.collection_stats["document_count"] == 3
    assert snapshot.runtime_status.dashboard_port == 8501
    assert snapshot.runtime_status.trace_file.endswith("logs\\traces.jsonl")
    assert snapshot.stats_error is None
