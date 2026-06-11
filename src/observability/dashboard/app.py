"""Streamlit Dashboard 多页面入口（G1）。"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

SRC_PATH = Path(__file__).resolve().parents[2]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard.pages import data_browser, ingestion_manager, overview


def _slugify_path(value: str) -> str:
    """把标题转换成稳定、唯一、可读的 URL path 片段。"""
    normalized = []
    for char in value.lower():
        if char.isascii() and char.isalnum():
            normalized.append(char)
        elif char in {" ", "-", "_"}:
            normalized.append("-")
    slug = "".join(normalized).strip("-")
    return slug or "page"


def _make_placeholder_page(title: str, task_id: str, description: str):
    """生成一个占位页面函数，供未完成页面先接入导航骨架。

    关键点：
    - `st.navigation()` 默认会从 callable 名称推导 URL pathname；
    - 如果所有占位页都复用同一个内部函数名，就会触发“pathname 重复”异常；
    - 因此这里显式为每个页面生成唯一函数名，确保导航系统能稳定区分页面。
    """

    def _render_placeholder() -> None:
        import streamlit as st

        st.title(title)
        st.info(f"{task_id} 尚未实现，当前阶段先保留导航入口。")
        st.caption(description)

    _render_placeholder.__name__ = f"placeholder_{task_id.lower()}_{_slugify_path(title).replace('-', '_')}"
    return _render_placeholder


def build_page_groups(st: Any) -> dict[str, list[Any]]:
    """构建 `st.navigation()` 需要的页面分组。

    做什么：
    - 注册 G1 已完成的 Overview 页面；
    - 把 G2-G6 先接成占位页，满足六页面导航架构验收；
    - 返回纯页面定义，便于单元测试直接断言导航结构。
    """
    return {
        "总览": [
            st.Page(overview.render, title="系统总览", url_path="overview"),
        ],
        "管理": [
            st.Page(
                data_browser.render,
                title="数据浏览器",
                url_path="data-browser",
            ),
            st.Page(
                ingestion_manager.render,
                title="Ingestion 管理",
                url_path="ingestion-manager",
            ),
        ],
        "追踪": [
            st.Page(
                _make_placeholder_page("Ingestion 追踪", "G5", "将展示摄取历史与阶段耗时瀑布图。"),
                title="Ingestion 追踪",
                url_path="ingestion-traces",
            ),
            st.Page(
                _make_placeholder_page("Query 追踪", "G6", "将展示查询历史、Dense/Sparse 对比与 Rerank 变化。"),
                title="Query 追踪",
                url_path="query-traces",
            ),
        ],
        "评估": [
            st.Page(
                _make_placeholder_page("评估面板", "H4", "后续阶段会接入自动化评估与趋势对比。"),
                title="评估面板",
                url_path="evaluation-panel",
            ),
        ],
    }


def main(st_module: Any | None = None) -> None:
    """启动 Streamlit 多页面应用。"""
    st = st_module or importlib.import_module("streamlit")
    st.set_page_config(page_title="Modular RAG Dashboard", page_icon=":material/dashboard:", layout="wide")

    navigation = st.navigation(build_page_groups(st))
    navigation.run()


if __name__ == "__main__":
    main()
