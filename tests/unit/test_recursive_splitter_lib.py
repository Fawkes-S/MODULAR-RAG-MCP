"""RecursiveSplitter 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("langchain_text_splitters")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from libs.splitter.recursive_splitter import RecursiveSplitter
from libs.splitter.splitter_factory import SplitterFactory


@pytest.fixture()
def isolated_registry() -> dict[str, object]:
    """隔离工厂注册表，避免测试互相污染。"""
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


def test_factory_can_create_recursive_provider(isolated_registry: dict[str, object]) -> None:
    """
    Given:
        `ingestion.splitter` 配置为 recursive，并设置 chunk_size/chunk_overlap。

    When:
        调用 SplitterFactory.create 创建切分器。

    Then:
        返回 RecursiveSplitter 实例。
    """
    splitter = SplitterFactory.create(
        {"ingestion": {"splitter": "recursive", "chunk_size": 64, "chunk_overlap": 8}}
    )
    assert isinstance(splitter, RecursiveSplitter)


def test_split_text_returns_non_empty_chunks_with_size_bound() -> None:
    """
    Given:
        一段包含标题、段落与代码块的 Markdown 文本。

    When:
        使用 RecursiveSplitter 进行切分。

    Then:
        - 返回非空 chunk 列表；
        - chunk 文本不为空；
        - chunk 长度不超过配置 chunk_size；
        - 原文关键内容可在切分结果中找到。
    """
    text = """# 标题一

段落一，包含一些说明文本。

```python
print('hello')
print('world')
```

## 标题二

段落二。"""

    splitter = RecursiveSplitter(chunk_size=40, chunk_overlap=10)
    chunks = splitter.split_text(text)

    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 40 for chunk in chunks)
    assert any("标题一" in chunk for chunk in chunks)
    assert any("标题二" in chunk for chunk in chunks)


def test_split_text_invalid_input_raises_readable_error() -> None:
    """
    Given:
        非字符串输入。

    When:
        调用 split_text。

    Then:
        抛出可读的 ValueError，提示输入类型错误。
    """
    splitter = RecursiveSplitter(chunk_size=100, chunk_overlap=20)

    with pytest.raises(ValueError, match="text must be str"):
        splitter.split_text(123)  # type: ignore[arg-type]


def test_splitter_parameter_validation_raises() -> None:
    """
    Given:
        非法 chunk 参数（chunk_size<=0 或 overlap>=size）。

    When:
        初始化 RecursiveSplitter。

    Then:
        立刻抛出 ValueError，阻止非法配置进入运行时。
    """
    with pytest.raises(ValueError, match="chunk_size"):
        RecursiveSplitter(chunk_size=0)

    with pytest.raises(ValueError, match="chunk_overlap"):
        RecursiveSplitter(chunk_size=10, chunk_overlap=10)
