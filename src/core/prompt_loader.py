"""Prompt template loading helpers.

统一处理：
- 从文件加载 prompt；
- 文件缺失/空内容时回退默认模板；
- 校验并补齐必须占位符（如 `{text}`）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence


def load_prompt_template(
    *,
    prompt_path: str | Path | None,
    default_template: str,
    required_placeholders: Sequence[str] | None = None,
    placeholder_append_blocks: Mapping[str, str] | None = None,
) -> str:
    """Load prompt template with fallback and placeholder guarantees.

    Args:
        prompt_path: Prompt 文件路径；为 `None` 时直接使用默认模板。
        default_template: 文件不可用时的回退模板，且必须是非空字符串。
        required_placeholders: 需要保证存在的占位符名称列表（不含花括号）。
        placeholder_append_blocks:
            当缺失占位符时追加的模板片段，键为占位符名称。
            例如：`{"text": "\\n\\n原文：\\n{text}"}`。

    Returns:
        处理后的 prompt 模板字符串。
    """
    template = ""
    if prompt_path is not None:
        try:
            template = Path(prompt_path).read_text(encoding="utf-8").strip()
        except Exception:
            template = ""

    if not template:
        template = default_template.strip()

    if not template:
        raise ValueError("default_template must be non-empty")

    append_blocks = dict(placeholder_append_blocks or {})
    for placeholder in required_placeholders or ():
        token = f"{{{placeholder}}}"
        if token in template:
            continue

        append_block = append_blocks.get(placeholder, f"\n\n{token}")
        template = f"{template.rstrip()}{append_block}"

    return template
