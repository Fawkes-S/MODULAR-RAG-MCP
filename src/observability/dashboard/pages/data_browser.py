"""Dashboard 数据浏览器页面（G3）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from observability.dashboard.services.data_service import BrowserChunk, BrowserImage, DataBrowserSnapshot, DataService


def render(data_service: DataService | None = None) -> None:
    """渲染数据浏览器页面。

    做什么：
    - 展示可过滤的文档列表；
    - 允许用户选中单个文档查看 chunk 正文、metadata 与关联图片；
    - 在空库或空过滤结果下给出明确提示，而不是显示一片空白。

    为什么采用“列表 + 选中文档详情”的两段式布局：
    - 先给用户全局视角，知道库里有什么；
    - 再给单文档深挖视角，避免一次性把所有 chunk 全铺开导致页面噪声过大。
    """
    import streamlit as st

    service = data_service or DataService()
    bootstrap_snapshot = service.build_browser_snapshot()

    st.title("数据浏览器")
    st.caption("浏览已摄入的文档、chunk 详情和关联图片，帮助快速检查索引内容是否符合预期。")

    selected_collection = _render_collection_filter(st, bootstrap_snapshot)
    snapshot = service.build_browser_snapshot(collection=selected_collection)

    _render_document_table(st, snapshot)
    if not snapshot.documents:
        return

    selected_doc_id = _render_document_picker(st, snapshot)
    detail_snapshot = service.build_browser_snapshot(
        collection=selected_collection,
        selected_doc_id=selected_doc_id,
    )
    _render_document_detail(st, detail_snapshot)


def _render_collection_filter(st: Any, snapshot: DataBrowserSnapshot) -> str | None:
    """渲染 collection 过滤器并返回当前选中的集合。"""
    options = ["<全部>"] + snapshot.collection_options
    selected_label = st.selectbox(
        "按集合过滤",
        options=options,
        index=0,
        help="先按 collection 缩小范围，再查看具体文档详情。",
    )
    return None if selected_label == "<全部>" else selected_label


def _render_document_table(st: Any, snapshot: DataBrowserSnapshot) -> None:
    """渲染文档列表视图。"""
    st.subheader("文档列表")

    if not snapshot.documents:
        if snapshot.active_collection is None:
            st.info("当前向量库还没有可浏览的文档。先执行 ingest，再回来查看。")
        else:
            st.info(f"集合 `{snapshot.active_collection}` 下暂无文档。请切换过滤条件或先摄入数据。")
        return

    rows = [
        {
            "source_path": item.source_path,
            "collection": item.collection or "-",
            "title": item.title,
            "doc_type": item.doc_type,
            "chunk_count": item.chunk_count,
            "image_count": item.image_count,
            "processed_at": item.processed_at or "-",
        }
        for item in snapshot.documents
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_document_picker(st: Any, snapshot: DataBrowserSnapshot) -> str:
    """渲染文档选择器，返回当前选中的 doc_id。"""
    document_ids = [item.doc_id for item in snapshot.documents]
    default_index = 0
    if snapshot.selected_document is not None:
        default_index = document_ids.index(snapshot.selected_document.doc_id)

    return st.selectbox(
        "展开查看文档详情",
        options=document_ids,
        index=default_index,
        format_func=lambda doc_id: _format_document_option(doc_id, snapshot),
        help="选择一份文档后，下方会展开它的 chunk 与图片详情。",
    )


def _render_document_detail(st: Any, snapshot: DataBrowserSnapshot) -> None:
    """渲染当前选中文档的详情区。"""
    document = snapshot.selected_document
    if document is None:
        return

    st.subheader("文档详情")
    metrics = st.columns(4)
    metrics[0].metric("Collection", document.collection or "-")
    metrics[1].metric("Chunks", document.chunk_count)
    metrics[2].metric("Images", document.image_count)
    metrics[3].metric("Processed", document.processed_at or "-")

    with st.container(border=True):
        st.write(f"**Source**: `{document.source_path}`")
        st.write(f"**Title**: {document.title}")
        st.write(f"**Doc Type**: {document.doc_type}")
        st.write(f"**File Hash**: `{document.file_hash or '-'}`")

    _render_chunks(st, snapshot.chunks)
    _render_images(st, snapshot.images)


def _render_chunks(st: Any, chunks: list[BrowserChunk]) -> None:
    """渲染 chunk 详情列表。"""
    st.subheader("Chunk 详情")
    if not chunks:
        st.info("当前文档没有可展示的 chunk 详情。")
        return

    for chunk in chunks:
        preview = chunk.text.replace("\n", " ").strip()
        if len(preview) > 80:
            preview = f"{preview[:80]}..."

        with st.expander(f"Chunk #{chunk.chunk_index} | {chunk.chunk_id} | {preview or '(empty)'}"):
            # 正文与 metadata 分开展示，避免用户在一团 JSON 中艰难找正文。
            st.markdown("**正文**")
            st.code(chunk.text or "", language="markdown")
            st.markdown("**Metadata**")
            st.json(chunk.metadata)


def _render_images(st: Any, images: list[BrowserImage]) -> None:
    """渲染关联图片预览。"""
    st.subheader("关联图片")
    if not images:
        st.info("当前文档没有关联图片。")
        return

    columns = st.columns(2)
    for index, image in enumerate(images):
        column = columns[index % len(columns)]
        with column:
            with st.container(border=True):
                st.caption(f"{image.image_id} | page={image.page_num or '-'}")
                path = Path(image.file_path)
                if path.exists():
                    st.image(str(path), use_container_width=True)
                else:
                    # 不让缺失文件直接把整页打挂，先把路径暴露出来方便排查。
                    st.warning("图片文件不存在，当前仅显示索引路径。")
                st.code(image.file_path, language="text")


def _format_document_option(doc_id: str, snapshot: DataBrowserSnapshot) -> str:
    """把 doc_id 格式化成更适合下拉框阅读的摘要文本。"""
    for item in snapshot.documents:
        if item.doc_id == doc_id:
            source_name = Path(item.source_path).name or item.source_path
            return f"{source_name} | {item.collection or '-'} | chunks={item.chunk_count}"
    return doc_id
