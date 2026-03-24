"""RecursiveSplitter 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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
    """Given provider=recursive, When 工厂创建, Then 返回 RecursiveSplitter。"""
    splitter = SplitterFactory.create({"splitter": {"provider": "recursive"}})

    assert isinstance(splitter, RecursiveSplitter)


def test_split_text_preserves_heading_and_code_block_boundary() -> None:
    """Given Markdown 含标题和代码块, When 切分, Then 标题与代码块不会被无意义打断。"""
    text = """# 标题一

段落一。

```python
print('hello')
print('world')
```

## 标题二

段落二。"""

    splitter = RecursiveSplitter(chunk_size=40, chunk_overlap=10, use_langchain=False)
    chunks = splitter.split_text(text)

    assert len(chunks) >= 2
    # 标题应完整出现在某个 chunk 中
    assert any("# 标题一" in chunk for chunk in chunks)
    assert any("## 标题二" in chunk for chunk in chunks)
    # 代码块围栏不应只出现一端（避免明显打断）
    for chunk in chunks:
        if "```" in chunk:
            assert chunk.count("```") in (0, 2)


def test_split_text_invalid_input_raises_readable_error() -> None:
    """Given 非字符串输入, When split_text, Then 抛出可读 ValueError。"""
    splitter = RecursiveSplitter(chunk_size=100, chunk_overlap=20, use_langchain=False)

    with pytest.raises(ValueError, match="text must be str"):
        splitter.split_text(123)  # type: ignore[arg-type]


def test_splitter_parameter_validation_raises() -> None:
    """Given 非法 chunk 参数, When 初始化 splitter, Then 立刻失败并提示约束。"""
    with pytest.raises(ValueError, match="chunk_size"):
        RecursiveSplitter(chunk_size=0)

    with pytest.raises(ValueError, match="chunk_overlap"):
        RecursiveSplitter(chunk_size=10, chunk_overlap=10)

