"""Dashboard Ingestion 管理页面（G4）。

这个页面负责把“人操作文件”的动作，翻译成后端真正能执行的两类管理行为：
- 上传 PDF 并触发 `IngestionPipeline.run(...)`；
- 选择已有文档并触发 `DocumentManager.delete_document(...)`。

为什么单独做这一页：
- G3 的数据浏览器解决的是“看当前库里有什么”；
- G4 则解决“把新文档放进来 / 把旧文档删掉”；
- 二者都面向文档管理，但前者偏只读，后者偏写操作，因此把写路径单独隔离更利于维护和排障。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import uuid4

from ingestion.document_manager import DeleteResult, DocumentInfo, DocumentManager
from ingestion.pipeline import IngestionPipeline, IngestionResult
from observability.dashboard.pages._table_utils import render_wrapped_dataframe
from observability.dashboard.services.config_service import ConfigService
from observability.dashboard.services.data_service import DataService

_SAFE_UPLOAD_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class UploadedFileLike(Protocol):
    """页面层关心的最小上传文件协议。

    Streamlit 的 `UploadedFile` 实际能力很多，但 G4 真正依赖的只有两件事：
    - `name`：用于保留用户能识别的原始文件名；
    - `getvalue()`：拿到上传的完整字节内容，落到本地临时文件后交给 pipeline。

    用 Protocol 而不是直接依赖具体 Streamlit 类型，可以让单元测试轻松注入 fake 对象，
    避免页面测试被 UI 框架本身牵着走。
    """

    name: str

    def getvalue(self) -> bytes: ...


@dataclass(frozen=True)
class IngestionManagerSnapshot:
    """Ingestion 管理页一次渲染所需的只读快照。"""

    collection_options: list[str] = field(default_factory=list)
    active_collection: str | None = None
    documents: list[DocumentInfo] = field(default_factory=list)


class IngestionManagerService:
    """为 G4 页面提供上传、列表、删除三类后端能力。

    做什么：
    - 复用 G3 的 `DataService` 读取文档列表与 collection 过滤选项；
    - 复用 C14/F5 的 `IngestionPipeline.run(..., on_progress=...)` 执行真实摄取；
    - 复用 G2 的 `DocumentManager.delete_document(...)` 执行跨存储删除。

    为什么：
    - Streamlit 页面天然更适合描述“交互流程”和“展示状态”；
    - 而上传暂存、依赖构建、删除调用、路径解析这些都属于后端编排细节；
    - 把它们收束在服务层后，页面函数就可以保持在“用户点击后发生什么”的层级。

    关键权衡：
    - 当前上传采用“先写入项目内临时目录，再交给 pipeline 读取”的同步模式。
      这比直接流式处理更简单，也与现有 `PdfLoader` 的文件路径输入契约完全一致。
    - 临时文件在单次操作完成后立即删除，而不是长期缓存。
      这样可以避免 Dashboard 上传目录慢慢变成第二份“隐形文档库”。

    失败路径：
    - 非 PDF、空文件、空 collection 会在进入 pipeline 前直接抛出 `ValueError`；
    - pipeline 或删除流程中的异常不在这里吞掉，而是向页面层抛出，
      让用户看到明确错误信息，并保留真实排障线索。
    """

    def __init__(
        self,
        *,
        settings_path: str | Path = "config/settings.yaml",
        config_service: ConfigService | None = None,
        data_service: DataService | None = None,
        pipeline: IngestionPipeline | None = None,
        document_manager: DocumentManager | None = None,
        upload_root: str | Path | None = None,
    ) -> None:
        self.config_service = config_service or ConfigService(settings_path)
        self._data_service = data_service
        self._pipeline = pipeline
        self._document_manager = document_manager
        self.upload_root = (
            Path(upload_root)
            if upload_root is not None
            else self._resolve_project_path("data/tmp/dashboard_uploads")
        )

    def build_snapshot(self, *, collection: str | None = None) -> IngestionManagerSnapshot:
        """构造 G4 页面需要的文档列表快照。

        做什么：
        - 复用 G3 `DataService.build_browser_snapshot()` 的文档聚合逻辑；
        - 只抽取 G4 真正需要的三个字段：collection 选项、当前过滤值、文档列表。

        为什么：
        - G4 和 G3 都在消费“文档视角”的数据；
        - 若两页各自发明一套聚合规则，很容易出现“浏览器里显示 3 份文档、管理页却显示 2 份”的偏差；
        - 直接复用 G3 现成结果，能保证 Dashboard 内部的文档认知一致。
        """
        browser_snapshot = self.data_service.build_browser_snapshot(collection=collection)
        return IngestionManagerSnapshot(
            collection_options=browser_snapshot.collection_options,
            active_collection=browser_snapshot.active_collection,
            documents=browser_snapshot.documents,
        )

    def ingest_uploaded_file(
        self,
        uploaded_file: UploadedFileLike,
        *,
        collection: str,
        force: bool = False,
        on_progress: Callable[[str, int, int], None] | None = None,
    ) -> IngestionResult:
        """将用户上传的 PDF 写入临时目录并触发真实摄取。

        做什么：
        - 校验上传对象、文件扩展名、文件内容与 collection；
        - 把上传字节落成临时 PDF 文件；
        - 调用 `IngestionPipeline.run()`，并把 G4 页面传入的进度回调原样转发；
        - 在流程结束后删除临时文件，避免项目目录积累无主上传残留。

        为什么不直接把字节流塞给 pipeline：
        - 现有 loader 契约是“接收一个真实文件路径”；
        - 若为了 G4 让 ingestion 主链路改成支持二进制流，会把原本清晰的文件型输入契约打散到多个组件；
        - 在当前阶段，临时落盘是最小改动、也最稳定的接入方式。

        关键权衡：
        - 这里优先保证与现有 CLI / loader 逻辑完全一致，而不是追求零磁盘中转；
        - 上传文件是写操作，因此专门放到 `data/tmp/dashboard_uploads`，避免污染正式数据目录。

        失败路径：
        - 非 PDF / 空文件 / 空 collection：抛 `ValueError`；
        - pipeline 失败：原样抛出，让页面展示真实错误；
        - 临时文件清理失败：不覆盖主异常，但会尽力在正常路径中删除。

        Args:
            uploaded_file: Streamlit 上传文件对象或兼容 fake。
            collection: 目标 collection。
            force: 是否强制重建。
            on_progress: 传给 pipeline 的进度回调。

        Returns:
            IngestionResult: pipeline 返回的标准执行结果。
        """
        safe_name = self._normalize_uploaded_name(getattr(uploaded_file, "name", ""))
        if safe_name.lower().endswith(".pdf") is False:
            raise ValueError("当前 Dashboard 只支持上传 PDF 文件。")

        normalized_collection = self._require_non_empty_collection(collection)
        payload = uploaded_file.getvalue()
        if not isinstance(payload, (bytes, bytearray)) or len(payload) == 0:
            raise ValueError("上传文件不能为空。")

        self.upload_root.mkdir(parents=True, exist_ok=True)
        staged_path = self.upload_root / f"{uuid4().hex}_{safe_name}"
        staged_path.write_bytes(bytes(payload))

        try:
            return self.pipeline.run(
                str(staged_path),
                collection=normalized_collection,
                force=force,
                logical_source_path=str(Path(uploaded_file.name).name),
                on_progress=on_progress,
            )
        finally:
            # 这里无论 pipeline 成功、失败还是跳过，都尝试把临时上传文件删掉。
            # G4 页面不是归档系统；一旦主流程结束，临时副本就不应继续留在磁盘里。
            if staged_path.exists():
                staged_path.unlink()

    def delete_document(self, *, source_path: str, collection: str) -> DeleteResult:
        """删除一份已摄取文档。"""
        return self.document_manager.delete_document(source_path, collection)

    @property
    def data_service(self) -> DataService:
        """懒加载 G3 DataService，保持文档列表视角与数据浏览器一致。"""
        if self._data_service is None:
            self._data_service = DataService(
                settings_path=self.config_service.settings_path,
                document_manager=self._document_manager,
            )
        return self._data_service

    @property
    def document_manager(self) -> DocumentManager:
        """优先复用 G3 DataService 内部的 DocumentManager。"""
        if self._document_manager is None:
            self._document_manager = self.data_service.document_manager
        return self._document_manager

    @property
    def pipeline(self) -> IngestionPipeline:
        """懒加载默认 IngestionPipeline，保持与 CLI 相同的配置驱动行为。"""
        if self._pipeline is None:
            settings = self.config_service.load_settings()
            self._pipeline = IngestionPipeline(settings=settings)
        return self._pipeline

    def _resolve_project_path(self, raw_path: str) -> Path:
        """把相对路径解析到当前项目根目录。"""
        path = Path(raw_path)
        if path.is_absolute():
            return path
        settings_path = self.config_service.settings_path.resolve()
        return (settings_path.parent.parent / path).resolve()

    @staticmethod
    def _normalize_uploaded_name(file_name: str) -> str:
        """把上传文件名收敛为安全的单层文件名。

        关键点：
        - 只保留 basename，避免用户传入带目录的名字影响最终落盘路径；
        - 把不安全字符替换为 `_`，防止临时目录里出现难以处理的特殊路径片段；
        - 若清洗后为空，则回退到稳定占位名。
        """
        candidate = Path(str(file_name).strip()).name
        sanitized = _SAFE_UPLOAD_NAME_PATTERN.sub("_", candidate).strip("._")
        return sanitized or "uploaded.pdf"

    @staticmethod
    def _require_non_empty_collection(collection: str) -> str:
        """校验 collection 文本，避免把空值拖到更深层才报错。"""
        if not isinstance(collection, str) or not collection.strip():
            raise ValueError("collection 不能为空。")
        return collection.strip()


def render(
    manager_service: IngestionManagerService | None = None,
    *,
    st_module: Any | None = None,
) -> None:
    """渲染 Ingestion 管理页。

    `st_module` 主要给单元测试使用：
    - 生产运行时不传，函数内部正常导入 Streamlit；
    - 测试时可传入 fake 对象，直接断言页面是否按预期调用 UI API。
    """
    if st_module is None:
        import streamlit as st
    else:
        st = st_module

    service = manager_service or IngestionManagerService()

    st.title("Ingestion 管理")
    st.caption("上传 PDF 触发摄取、观察实时进度，并对已摄取文档执行删除。")

    _render_upload_panel(st, service)
    _render_delete_panel(st, service)


def _render_upload_panel(st: Any, service: IngestionManagerService) -> None:
    """渲染上传与摄取触发区。"""
    st.subheader("上传并摄取")
    with st.container(border=True):
        collection = st.text_input(
            "写入 collection",
            value="default",
            help="摄取后的 chunk 会按 collection 写入向量库与图片索引，后续检索和管理页都会依赖这个字段。",
        )
        force = st.checkbox(
            "强制重建",
            value=False,
            help="开启后会忽略完整性跳过逻辑，即使文件内容未变化也会重新执行整条摄取链路。",
        )
        uploaded_file = st.file_uploader(
            "选择 PDF 文件",
            type=["pdf"],
            accept_multiple_files=False,
            help="当前 Dashboard 复用的是 PDF Loader，因此这里仅开放 PDF 上传入口。",
        )

        if uploaded_file is None:
            st.info("选择一个 PDF 后，再点击“开始摄取”。")

        start_requested = st.button(
            "开始摄取",
            type="primary",
            use_container_width=True,
            disabled=uploaded_file is None,
        )
        if start_requested is False or uploaded_file is None:
            return

        progress_bar = st.progress(0.0, text="准备启动摄取...")
        progress_log = st.empty()

        def _on_progress(stage_name: str, current: int, total: int) -> None:
            ratio = 0.0 if total <= 0 else min(max(current / total, 0.0), 1.0)
            progress_bar.progress(
                ratio,
                text=f"阶段：{_format_stage_name(stage_name)} ({current}/{total})",
            )
            # 这里额外保留一条文本状态，便于用户知道“现在卡在哪一步”，
            # 而不只是看见一个会动的进度条。
            progress_log.caption(f"最近完成阶段：{_format_stage_name(stage_name)}")

        try:
            result = service.ingest_uploaded_file(
                uploaded_file,
                collection=collection,
                force=force,
                on_progress=_on_progress,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"摄取失败：{type(exc).__name__}: {exc}")
            return

        progress_bar.progress(1.0, text="摄取流程结束")
        if result.skipped:
            st.warning(
                f"文件命中增量跳过：file_hash={result.file_hash}。"
                "如果你希望强制重新处理，请勾选“强制重建”。"
            )
            return

        st.success(
            "摄取完成："
            f"chunks={result.chunk_count} / vectors={len(result.vector_ids)} / "
            f"images={result.image_count} / bm25_terms={result.bm25_terms}"
        )


def _render_delete_panel(st: Any, service: IngestionManagerService) -> None:
    """渲染已摄取文档列表与删除入口。"""
    st.subheader("管理已摄取文档")
    with st.container(border=True):
        bootstrap_snapshot = service.build_snapshot()
        selected_collection = _render_collection_filter(st, bootstrap_snapshot)
        snapshot = service.build_snapshot(collection=selected_collection)

        if not snapshot.documents:
            if selected_collection is None:
                st.info("当前还没有可管理的文档。先上传 PDF 完成一次摄取。")
            else:
                st.info(f"collection `{selected_collection}` 下当前没有文档。")
            return

        selected_doc_id = st.selectbox(
            "选择待管理文档",
            options=[item.doc_id for item in snapshot.documents],
            format_func=lambda doc_id: _format_document_option(doc_id, snapshot.documents),
            help="先选中文档，再决定是否删除；这样可以避免把删除按钮铺满整个列表，降低误触概率。",
        )
        selected_document = _find_document(snapshot.documents, selected_doc_id)

        if selected_document is None:
            st.warning("当前未能解析选中文档，请重新选择。")
            return

        if selected_document.collection is None:
            # 删除操作需要明确 collection，才能安全命中 Chroma/ImageStorage 对应数据。
            st.warning("该文档缺少 collection 信息，当前无法安全删除。")
        else:
            delete_requested = st.button(
                "删除选中文档",
                type="secondary",
                use_container_width=True,
            )
            if delete_requested:
                try:
                    result = service.delete_document(
                        source_path=selected_document.source_path,
                        collection=selected_document.collection,
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"删除失败：{type(exc).__name__}: {exc}")
                else:
                    st.success(_format_delete_result(result))
                    # 删除后立即重新取快照，确保当前这次渲染就能看到更新后的列表，
                    # 而不是等下一次用户交互才刷新。
                    snapshot = service.build_snapshot(collection=selected_collection)

        _render_document_table(st, snapshot.documents)


def _render_collection_filter(st: Any, snapshot: IngestionManagerSnapshot) -> str | None:
    """渲染 collection 过滤器。"""
    options = ["<全部>"] + snapshot.collection_options
    selected_label = st.selectbox(
        "按 collection 过滤文档",
        options=options,
        index=0,
        help="先按 collection 缩小范围，再操作单份文档，可以减少误删风险。",
    )
    return None if selected_label == "<全部>" else selected_label


def _render_document_table(st: Any, documents: list[DocumentInfo]) -> None:
    """把文档列表渲染成紧凑表格。"""
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
        for item in documents
    ]
    render_wrapped_dataframe(st, rows)


def _find_document(documents: list[DocumentInfo], doc_id: str) -> DocumentInfo | None:
    """在当前文档列表中解析选中的文档对象。"""
    for item in documents:
        if item.doc_id == doc_id:
            return item
    return None


def _format_document_option(doc_id: str, documents: list[DocumentInfo]) -> str:
    """把文档选项格式化为更适合下拉框阅读的摘要文本。"""
    document = _find_document(documents, doc_id)
    if document is None:
        return doc_id
    return (
        f"{Path(document.source_path).name} | "
        f"{document.collection or '-'} | "
        f"chunks={document.chunk_count} | images={document.image_count}"
    )


def _format_stage_name(stage_name: str) -> str:
    """把 F5 阶段名转成更适合页面展示的文案。"""
    mapping = {
        "load": "加载文档",
        "split": "切分文档",
        "transform": "增强内容",
        "embed": "生成向量",
        "upsert": "写入存储",
    }
    return mapping.get(stage_name, stage_name)


def _format_delete_result(result: DeleteResult) -> str:
    """格式化删除结果摘要。"""
    message = (
        "删除完成："
        f"chunks={result.chunks_deleted} / "
        f"bm25={result.bm25_deleted} / "
        f"images={result.images_deleted} / "
        f"integrity={result.integrity_deleted}"
    )
    if result.fallback_used and result.fallback_reason:
        message += f"（已走兼容回退：{result.fallback_reason}）"
    return message
