"""Dashboard 多页面入口测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from observability.dashboard import app
from observability.dashboard.pages import data_browser


class _FakeNavigation:
    """模拟 `st.navigation()` 返回对象。"""

    def __init__(self, owner: "_FakeStreamlit") -> None:
        self.owner = owner

    def run(self) -> None:
        self.owner.navigation_ran = True


class _FakeStreamlit:
    """最小 fake streamlit，只覆盖 G1 入口用到的 API。"""

    def __init__(self) -> None:
        self.page_config: dict[str, Any] = {}
        self.page_groups: dict[str, list[dict[str, Any]]] = {}
        self.navigation_ran = False

    def set_page_config(self, **kwargs: Any) -> None:
        self.page_config = kwargs

    def Page(self, render: Any, title: str, url_path: str | None = None) -> dict[str, Any]:  # noqa: N802
        return {"render": render, "title": title, "url_path": url_path}

    def navigation(self, page_groups: dict[str, list[dict[str, Any]]]) -> _FakeNavigation:
        self.page_groups = page_groups
        return _FakeNavigation(self)


def test_dashboard_app_registers_overview_and_placeholder_pages() -> None:
    """
    Given:
        一个只实现 `Page/navigation/set_page_config` 的假 Streamlit 对象。

    When:
        调用 `app.main(st_module=fake_streamlit)` 启动 Dashboard 入口。

    Then:
        - 页面配置应被设置；
        - `st.navigation()` 应注册 6 个页面；
        - Overview 与其余占位页面都应进入导航；
        - 最终会调用 `navigation.run()`。
    """
    fake_streamlit = _FakeStreamlit()

    app.main(st_module=fake_streamlit)

    titles = [page["title"] for group in fake_streamlit.page_groups.values() for page in group]
    url_paths = [page["url_path"] for group in fake_streamlit.page_groups.values() for page in group]
    assert fake_streamlit.page_config["page_title"] == "Modular RAG Dashboard"
    assert titles == [
        "系统总览",
        "数据浏览器",
        "Ingestion 管理",
        "Ingestion 追踪",
        "Query 追踪",
        "评估面板",
    ]
    assert len(url_paths) == len(set(url_paths))
    assert fake_streamlit.page_groups["管理"][0]["render"] is data_browser.render
    assert fake_streamlit.navigation_ran is True
