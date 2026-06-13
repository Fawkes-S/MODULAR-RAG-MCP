"""Dashboard 表格渲染辅助函数。"""

from __future__ import annotations

from typing import Any

_WRAPPED_DATAFRAME_STYLE = """
<style>
[data-testid="stDataFrame"] div[role="columnheader"],
[data-testid="stDataFrame"] div[role="gridcell"] {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.4 !important;
}

[data-testid="stDataFrame"] div[role="row"] {
    max-height: none !important;
}
</style>
"""


def render_wrapped_dataframe(
    st: Any,
    rows: list[dict[str, object]],
    *,
    use_container_width: bool = True,
    hide_index: bool = True,
) -> None:
    """渲染一个默认支持长文本换行的 Dashboard 表格。

    做什么：
    - 在输出 `st.dataframe(...)` 之前注入一段表格样式；
    - 让长 `text/source_path` 字段优先完整显示，而不是被省略号截断。

    为什么：
    - 多个 Dashboard 页面都要展示长正文和长路径；
    - 把换行策略收口到一个 helper，能避免每个页面各自实现、各自走样。

    关键权衡：
    - 这里选择最小侵入的样式注入，而不是整体替换表格组件；
    - 这样改动面小，但会依赖 Streamlit 当前 DataFrame DOM 结构。

    失败路径：
    - 如果测试桩没有 `markdown()`，则跳过样式注入，只保留数据展示；
    - 即使样式未来失效，表格仍可正常显示，只是退回默认截断样式。
    """
    if hasattr(st, "markdown"):
        st.markdown(_WRAPPED_DATAFRAME_STYLE, unsafe_allow_html=True)
    st.dataframe(rows, use_container_width=use_container_width, hide_index=hide_index)
