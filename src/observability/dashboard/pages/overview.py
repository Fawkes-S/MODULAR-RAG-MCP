"""Dashboard 系统总览页（G1）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from libs.vector_store.chroma_store import ChromaStore
from observability.dashboard.services.config_service import ComponentCard, ConfigService, RuntimeStatus


@dataclass(frozen=True)
class OverviewSnapshot:
    """Overview 页面渲染前的聚合数据快照。"""

    component_cards: list[ComponentCard]
    runtime_status: RuntimeStatus
    collection_stats: dict[str, Any]
    stats_error: str | None = None


def build_overview_snapshot(
    config_service: ConfigService | None = None,
    vector_store: ChromaStore | Any | None = None,
) -> OverviewSnapshot:
    """收集 Overview 页面需要的所有数据。

    做什么：
    - 读取 Dashboard 组件卡片与运行状态；
    - 从向量库提取当前 collection 统计；
    - 把“查询失败但页面仍可展示”的错误降级为 `stats_error` 文本。

    为什么：
    - 页面渲染函数里如果混入太多 I/O，会很难测试；
    - 先构造纯数据快照，再交给 `render()` 输出，能让单元测试直接断言核心行为。

    关键权衡：
    - 这里只对“统计读取失败”做降级，因为 Dashboard 总览页不能因为统计出错就整页崩掉；
    - 但配置读取仍保持 fail-fast，因为没有 Settings 时页面含义已经不存在。

    失败路径：
    - 若 Chroma 初始化或统计失败，返回空统计并写入 `stats_error`；
    - 调用方可继续渲染组件配置与运行状态，帮助定位问题。
    """
    service = config_service or ConfigService()
    settings = service.load_settings()

    stats_error: str | None = None
    if vector_store is None:
        vector_store = ChromaStore(persist_dir=settings.vector_store.persist_dir)

    try:
        collection_stats = vector_store.get_collection_stats()
    except Exception as exc:  # noqa: BLE001
        # 这里故意把错误转成可展示文本，避免向量库局部故障拖垮整页 Dashboard。
        collection_stats = {
            "collection_name": "unavailable",
            "chunk_count": 0,
            "document_count": 0,
            "image_count": 0,
            "collections": [],
        }
        stats_error = f"{type(exc).__name__}: {exc}"

    return OverviewSnapshot(
        component_cards=service.build_component_cards(),
        runtime_status=service.build_runtime_status(),
        collection_stats=collection_stats,
        stats_error=stats_error,
    )


def render(config_service: ConfigService | None = None, vector_store: ChromaStore | Any | None = None) -> None:
    """渲染系统总览页。"""
    import streamlit as st

    snapshot = build_overview_snapshot(config_service=config_service, vector_store=vector_store)

    st.title("系统总览")
    st.caption("展示当前可插拔组件配置、向量库统计以及 Dashboard 运行状态。")

    _render_component_cards(st, snapshot.component_cards)
    _render_collection_stats(st, snapshot.collection_stats, snapshot.stats_error)
    _render_runtime_status(st, snapshot.runtime_status)


def _render_component_cards(st: Any, cards: list[ComponentCard]) -> None:
    """渲染组件配置卡片。"""
    st.subheader("组件配置")

    # 两列排版在桌面端更像“卡片区”，同时移动端也会自动纵向折叠，不会挤成一行。
    for start in range(0, len(cards), 2):
        columns = st.columns(2)
        for column, card in zip(columns, cards[start : start + 2], strict=False):
            with column:
                with st.container(border=True):
                    st.markdown(f"### {card.title}")
                    st.write(card.summary)
                    for detail in card.details:
                        st.caption(detail)


def _render_collection_stats(st: Any, stats: dict[str, Any], stats_error: str | None) -> None:
    """渲染向量库数据资产统计。"""
    st.subheader("数据资产统计")

    if stats_error:
        st.warning(f"当前无法读取向量库统计，已降级显示空值：{stats_error}")

    metric_columns = st.columns(3)
    metric_columns[0].metric("文档数", int(stats.get("document_count", 0)))
    metric_columns[1].metric("Chunk 数", int(stats.get("chunk_count", 0)))
    metric_columns[2].metric("图片数", int(stats.get("image_count", 0)))

    collection_rows = stats.get("collections", [])
    if isinstance(collection_rows, list) and collection_rows:
        st.dataframe(collection_rows, use_container_width=True, hide_index=True)
    else:
        st.info("当前向量库还没有可展示的数据。先执行 ingest，再回来查看统计。")


def _render_runtime_status(st: Any, runtime_status: RuntimeStatus) -> None:
    """渲染 Dashboard 与 trace 文件的健康状态。"""
    st.subheader("运行状态")

    with st.container(border=True):
        st.write(f"Dashboard 端口：`{runtime_status.dashboard_port}`")
        st.write(f"Trace 目录：`{runtime_status.traces_dir}`")
        st.write(f"Trace 文件：`{runtime_status.trace_file}`")
        st.write(
            f"自动刷新：`{runtime_status.auto_refresh}` / 间隔 "
            f"`{runtime_status.refresh_interval}s`"
        )
        st.write(f"Trace 文件存在：`{runtime_status.trace_file_exists}`")
        st.write(f"最近一次 Trace 写入：`{runtime_status.last_trace_at}`")
