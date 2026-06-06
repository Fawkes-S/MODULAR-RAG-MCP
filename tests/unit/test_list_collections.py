"""list_collections tool 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from mcp_server.protocol_handler import ProtocolHandlerError  # noqa: E402
from mcp_server.tools.list_collections import ListCollectionsTool  # noqa: E402


def test_list_collections_returns_sorted_collection_names_from_directory_tree(tmp_path: Path) -> None:
    """
    Given:
        一个模拟的 `data/documents` 目录，下面包含多个一级集合目录，以及目录内的普通文件和子目录。
    When:
        调用 `ListCollectionsTool.handle({})`。
    Then:
        应按集合名稳定排序返回集合列表，并附带每个集合的轻量统计信息。
    """
    documents_root = tmp_path / "data" / "documents"
    alpha = documents_root / "alpha"
    beta = documents_root / "beta"
    beta_nested = beta / "nested"
    alpha.mkdir(parents=True)
    beta_nested.mkdir(parents=True)
    (alpha / "a.pdf").write_text("a", encoding="utf-8")
    (alpha / "b.md").write_text("b", encoding="utf-8")
    (beta / "c.pdf").write_text("c", encoding="utf-8")

    payload = ListCollectionsTool(documents_root=str(documents_root)).handle({})

    collections = payload["structuredContent"]["collections"]
    assert [item["name"] for item in collections] == ["alpha", "beta"]
    assert collections[0]["file_count"] == 2
    assert collections[0]["subdir_count"] == 0
    assert collections[1]["file_count"] == 1
    assert collections[1]["subdir_count"] == 1
    assert "alpha" in payload["content"][0]["text"]
    assert "beta" in payload["content"][0]["text"]


def test_list_collections_returns_empty_message_when_documents_root_missing(tmp_path: Path) -> None:
    """
    Given:
        一个不存在的 `data/documents` 根目录。
    When:
        调用 `ListCollectionsTool.handle({})`。
    Then:
        不应抛异常，而应返回空集合列表和友好提示文本。
    """
    missing_root = tmp_path / "missing" / "documents"

    payload = ListCollectionsTool(documents_root=str(missing_root)).handle({})

    assert payload["structuredContent"]["count"] == 0
    assert payload["structuredContent"]["collections"] == []
    assert "没有可用的知识库集合" in payload["content"][0]["text"]


def test_list_collections_rejects_unexpected_arguments(tmp_path: Path) -> None:
    """
    Given:
        `list_collections` 按规格不接收任何业务参数。
    When:
        传入额外 arguments 调用 tool。
    Then:
        应返回协议级 `Invalid params` 错误，而不是静默忽略。
    """
    tool = ListCollectionsTool(documents_root=str(tmp_path))

    with pytest.raises(ProtocolHandlerError, match="Invalid params"):
        tool.handle({"unexpected": True})
