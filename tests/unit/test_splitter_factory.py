"""SplitterFactory 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.splitter.base_splitter import BaseSplitter
from libs.splitter.splitter_factory import SplitterFactory


class _RecursiveFakeSplitter(BaseSplitter):
    """模拟 Recursive 策略：按空行切分。"""

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]


class _SemanticFakeSplitter(BaseSplitter):
    """模拟 Semantic 策略：按句号切分。"""

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [chunk.strip() for chunk in text.split(".") if chunk.strip()]


class _FixedFakeSplitter(BaseSplitter):
    """模拟 Fixed 策略：每 5 个字符切分。"""

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [text[i : i + 5] for i in range(0, len(text), 5)]


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂全局注册表，避免测试污染。"""
    snapshot = dict(SplitterFactory._registry)
    SplitterFactory._registry.clear()
    try:
        yield snapshot
    finally:
        SplitterFactory._registry.clear()
        SplitterFactory._registry.update(snapshot)


def test_factory_routes_recursive_provider(isolated_registry: dict[str, object]) -> None:
    """验证 recursive provider 会路由到对应实现，并按空行完成切分。"""
    SplitterFactory.register("recursive", _RecursiveFakeSplitter)
    splitter = SplitterFactory.create({"splitter": {"provider": "recursive"}})

    assert isinstance(splitter, _RecursiveFakeSplitter)
    assert splitter.split_text("a\n\n b\n\n c") == ["a", "b", "c"]


def test_factory_routes_semantic_provider(isolated_registry: dict[str, object]) -> None:
    """验证 semantic provider 路由正确，并按句号切分文本。"""
    SplitterFactory.register("semantic", _SemanticFakeSplitter)
    splitter = SplitterFactory.create({"splitter": {"provider": "semantic"}})

    assert isinstance(splitter, _SemanticFakeSplitter)
    assert splitter.split_text("A. B. C") == ["A", "B", "C"]


def test_factory_routes_fixed_provider(isolated_registry: dict[str, object]) -> None:
    """验证 fixed provider 路由正确，并按定长窗口切分。"""
    SplitterFactory.register("fixed", _FixedFakeSplitter)
    splitter = SplitterFactory.create({"splitter": {"provider": "fixed"}})

    assert isinstance(splitter, _FixedFakeSplitter)
    assert splitter.split_text("abcdefghij") == ["abcde", "fghij"]


def test_factory_missing_provider_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """验证缺少 `splitter.provider` 时报错信息可直接定位字段。"""
    with pytest.raises(ValueError, match="splitter.provider"):
        SplitterFactory.create({"splitter": {}})


def test_factory_unknown_provider_raises(isolated_registry: dict[str, object]) -> None:
    """验证未知 splitter provider 会被拒绝，避免静默使用错误策略。"""
    with pytest.raises(ValueError, match="Unknown splitter provider: unknown"):
        SplitterFactory.create({"splitter": {"provider": "unknown"}})
