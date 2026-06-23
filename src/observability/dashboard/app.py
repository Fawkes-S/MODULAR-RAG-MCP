"""Streamlit Dashboard 多页面入口。

该模块只负责注册页面和启动导航，不放具体业务逻辑。
各页面自己的数据读取、异常降级和渲染细节放在 `pages/` 与 `services/` 下。
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

SRC_PATH = Path(__file__).resolve().parents[2]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard.pages import (  # noqa: E402
    data_browser,
    evaluation_panel,
    ingestion_manager,
    ingestion_traces,
    overview,
    query_traces,
)


def build_page_groups(st: Any) -> dict[str, list[Any]]:
    """构建 `st.navigation()` 使用的页面分组。

    做什么：
    - 注册 Dashboard 的六个主页面；
    - 为每个页面设置稳定、唯一的 `url_path`；
    - 返回纯页面定义，方便单元测试直接断言导航结构。

    为什么：
    - Streamlit 会根据页面 callable/title 推导 URL；显式指定 `url_path` 可以避免乱码标题、
      重名函数或占位页造成路径冲突；
    - 页面注册集中在入口文件，后续新增/替换页面时只需要改一处。

    关键权衡：
    - 入口层不捕获页面异常。页面内部应自行处理可降级错误；
    - 配置读取、数据查询、评估运行等重逻辑不放这里，避免启动入口变成业务编排层。
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
                ingestion_traces.render,
                title="Ingestion 追踪",
                url_path="ingestion-traces",
            ),
            st.Page(
                query_traces.render,
                title="Query 追踪",
                url_path="query-traces",
            ),
        ],
        "评估": [
            st.Page(
                evaluation_panel.render,
                title="评估面板",
                url_path="evaluation-panel",
            ),
        ],
    }


def main(st_module: Any | None = None) -> None:
    """启动 Streamlit 多页面 Dashboard。"""
    st = st_module or importlib.import_module("streamlit")
    st.set_page_config(page_title="Modular RAG Dashboard", page_icon=":material/dashboard:", layout="wide")

    navigation = st.navigation(build_page_groups(st))
    navigation.run()


if __name__ == "__main__":
    main()
