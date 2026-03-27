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

    def __init__(self, **_: object) -> None:
        pass

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]


class _SemanticFakeSplitter(BaseSplitter):
    """模拟 Semantic 策略：按句号切分。"""

    def __init__(self, **_: object) -> None:
        pass

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [chunk.strip() for chunk in text.split(".") if chunk.strip()]


class _FixedFakeSplitter(BaseSplitter):
    """模拟 Fixed 策略：每 5 个字符切分。"""

    def __init__(self, **_: object) -> None:
        pass

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [text[i : i + 5] for i in range(0, len(text), 5)]


class _EchoKwargsSplitter(BaseSplitter):
    """用于验证 splitter_kwargs/override_kwargs 是否被正确传递。"""

    def __init__(self, token: str = "", chunk_size: int = 0, **_: object) -> None:
        self.token = token
        self.chunk_size = int(chunk_size)

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return [f"{self.token}:{self.chunk_size}:{text}"]


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂全局注册表，避免测试污染。"""
    snapshot = dict(SplitterFactory._registry)
    snapshot_builtin = SplitterFactory._builtin_loaded
    SplitterFactory._registry.clear()
    SplitterFactory._builtin_loaded = False
    try:
        yield snapshot
    finally:
        SplitterFactory._registry.clear()
        SplitterFactory._registry.update(snapshot)
        SplitterFactory._builtin_loaded = snapshot_builtin


def test_factory_routes_recursive_provider(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        已注册 recursive provider，且配置路径为 `ingestion.splitter`。

    When:
        调用 SplitterFactory.create 创建 splitter。

    Then:
        返回 _RecursiveFakeSplitter 实例；
        并且按空行切分文本结果正确。
    """
    SplitterFactory.register("recursive", _RecursiveFakeSplitter)
    splitter = SplitterFactory.create({"ingestion": {"splitter": "recursive"}})

    assert isinstance(splitter, _RecursiveFakeSplitter)
    assert splitter.split_text("a\n\n b\n\n c") == ["a", "b", "c"]


def test_factory_routes_semantic_provider(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        已注册 semantic provider。

    When:
        调用 SplitterFactory.create 创建 splitter。

    Then:
        返回 _SemanticFakeSplitter 实例；
        并且按句号切分结果正确。
    """
    SplitterFactory.register("semantic", _SemanticFakeSplitter)
    splitter = SplitterFactory.create({"ingestion": {"splitter": "semantic"}})

    assert isinstance(splitter, _SemanticFakeSplitter)
    assert splitter.split_text("A. B. C") == ["A", "B", "C"]


def test_factory_routes_fixed_provider(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        已注册 fixed provider。

    When:
        调用 SplitterFactory.create 创建 splitter。

    Then:
        返回 _FixedFakeSplitter 实例；
        并且按定长窗口切分结果正确。
    """
    SplitterFactory.register("fixed", _FixedFakeSplitter)
    splitter = SplitterFactory.create({"ingestion": {"splitter": "fixed"}})

    assert isinstance(splitter, _FixedFakeSplitter)
    assert splitter.split_text("abcdefghij") == ["abcde", "fghij"]


def test_factory_passes_ingestion_splitter_kwargs_and_common_kwargs(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        ingestion 中包含 `chunk_size` 与 `splitter_kwargs`。

    When:
        工厂创建 provider。

    Then:
        provider 能收到并使用这些参数。
    """
    SplitterFactory.register("echo", _EchoKwargsSplitter)
    splitter = SplitterFactory.create(
        {
            "ingestion": {
                "splitter": "echo",
                "chunk_size": 12,
                "splitter_kwargs": {"token": "ok"},
            }
        }
    )

    assert isinstance(splitter, _EchoKwargsSplitter)
    assert splitter.split_text("abc") == ["ok:12:abc"]


def test_factory_override_kwargs_take_highest_precedence(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        配置里已有 splitter_kwargs.token。

    When:
        create() 传入 override_kwargs 覆盖同名参数。

    Then:
        override_kwargs 优先生效。
    """
    SplitterFactory.register("echo", _EchoKwargsSplitter)
    splitter = SplitterFactory.create(
        {"ingestion": {"splitter": "echo", "splitter_kwargs": {"token": "from_cfg"}}},
        token="from_override",
        chunk_size=99,
    )

    assert isinstance(splitter, _EchoKwargsSplitter)
    assert splitter.split_text("abc") == ["from_override:99:abc"]


def test_factory_missing_provider_path_raises_readable_error(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        ingestion 配置中缺少 splitter 字段。

    When:
        调用 SplitterFactory.create。

    Then:
        抛出包含 `ingestion.splitter` 路径提示的可读错误。
    """
    with pytest.raises(ValueError, match="ingestion.splitter"):
        SplitterFactory.create({"ingestion": {}})


def test_factory_unknown_provider_raises(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        未注册的 provider（unknown）。

    When:
        调用 SplitterFactory.create。

    Then:
        明确抛出 Unknown splitter provider 错误。
    """
    with pytest.raises(ValueError, match="Unknown splitter provider: unknown"):
        SplitterFactory.create({"ingestion": {"splitter": "unknown"}})
