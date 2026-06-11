"""Dashboard Ingestion 管理页测试（G4）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ingestion.document_manager import DeleteResult, DocumentInfo
from ingestion.pipeline import IngestionResult
from observability.dashboard.pages.ingestion_manager import (  # noqa: E402
    IngestionManagerService,
    IngestionManagerSnapshot,
    render,
)


class _FakeUploadedFile:
    """测试桩：模拟 Streamlit 上传文件对象。"""

    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


class _FakePipeline:
    """测试桩：记录 G4 页面如何调用 pipeline。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        source_path: str,
        collection: str = "default",
        *,
        force: bool = False,
        trace: Any | None = None,
        on_progress: Any | None = None,
    ) -> IngestionResult:
        _ = trace
        self.calls.append(
            {
                "source_path": source_path,
                "collection": collection,
                "force": force,
                "file_exists_during_call": Path(source_path).exists(),
            }
        )
        if on_progress is not None:
            on_progress("load", 1, 3)
            on_progress("transform", 2, 3)
            on_progress("upsert", 3, 3)
        return IngestionResult(
            source_path=source_path,
            collection=collection,
            file_hash="hash-demo",
            skipped=False,
            document_id="doc_demo",
            chunk_count=2,
            vector_ids=["chunk_a", "chunk_b"],
            image_count=1,
            bm25_terms=7,
            trace_id="trace-demo",
        )


class _FakeContext:
    """测试桩：模拟 `with st.container(...):` 返回对象。"""

    def __enter__(self) -> "_FakeContext":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        _ = (exc_type, exc, tb)
        return False


class _FakePlaceholder:
    """测试桩：模拟 `st.empty()` 返回占位对象。"""

    def __init__(self, owner: "_FakeStreamlit") -> None:
        self.owner = owner

    def caption(self, text: str) -> None:
        self.owner.placeholder_captions.append(text)


class _FakeProgressBar:
    """测试桩：记录进度条更新。"""

    def __init__(self, owner: "_FakeStreamlit") -> None:
        self.owner = owner

    def progress(self, value: float, text: str | None = None) -> None:
        self.owner.progress_updates.append((value, text))


class _FakeStreamlit:
    """最小 fake Streamlit，实现 G4 页面渲染需要的 API。"""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.dataframes: list[list[dict[str, Any]]] = []
        self.placeholder_captions: list[str] = []
        self.progress_updates: list[tuple[float, str | None]] = []

        self._text_inputs = {"写入 collection": "demo"}
        self._checkboxes = {"强制重建": True}
        self._file_uploads = {"选择 PDF 文件": _FakeUploadedFile("alpha.pdf", b"%PDF-demo")}
        self._buttons = {
            "开始摄取": True,
            "删除选中文档": True,
        }
        self._selectboxes = {
            "按 collection 过滤文档": "demo",
            "选择待管理文档": "memory://docs/existing.pdf",
        }

    def title(self, text: str) -> None:
        self.messages.append(("title", text))

    def caption(self, text: str) -> None:
        self.messages.append(("caption", text))

    def subheader(self, text: str) -> None:
        self.messages.append(("subheader", text))

    def container(self, border: bool = False) -> _FakeContext:
        _ = border
        return _FakeContext()

    def text_input(self, label: str, value: str = "", help: str | None = None) -> str:
        _ = (value, help)
        return self._text_inputs.get(label, value)

    def checkbox(self, label: str, value: bool = False, help: str | None = None) -> bool:
        _ = help
        return self._checkboxes.get(label, value)

    def file_uploader(self, label: str, **kwargs: Any) -> Any:
        _ = kwargs
        return self._file_uploads.get(label)

    def button(self, label: str, disabled: bool = False, **kwargs: Any) -> bool:
        _ = kwargs
        if disabled:
            return False
        return self._buttons.get(label, False)

    def progress(self, value: float, text: str | None = None) -> _FakeProgressBar:
        self.progress_updates.append((value, text))
        return _FakeProgressBar(self)

    def empty(self) -> _FakePlaceholder:
        return _FakePlaceholder(self)

    def selectbox(
        self,
        label: str,
        options: list[Any],
        index: int = 0,
        format_func: Any | None = None,
        help: str | None = None,
    ) -> Any:
        _ = (index, format_func, help)
        selected = self._selectboxes.get(label, options[0] if options else None)
        return selected if selected in options else (options[0] if options else None)

    def dataframe(self, rows: list[dict[str, Any]], **kwargs: Any) -> None:
        _ = kwargs
        self.dataframes.append(rows)

    def info(self, text: str) -> None:
        self.messages.append(("info", text))

    def success(self, text: str) -> None:
        self.messages.append(("success", text))

    def warning(self, text: str) -> None:
        self.messages.append(("warning", text))

    def error(self, text: str) -> None:
        self.messages.append(("error", text))


class _FakeManagerService:
    """测试桩：同时模拟上传、删除与文档列表刷新。"""

    def __init__(self) -> None:
        self.ingest_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.deleted = False

    def build_snapshot(self, *, collection: str | None = None) -> IngestionManagerSnapshot:
        _ = collection
        if self.deleted:
            documents: list[DocumentInfo] = []
        else:
            documents = [
                DocumentInfo(
                    doc_id="memory://docs/existing.pdf",
                    source_path="memory://docs/existing.pdf",
                    collection="demo",
                    title="Existing Guide",
                    doc_type="pdf",
                    chunk_count=3,
                    image_count=1,
                    processed_at="2026-06-10 09:00:00",
                    file_hash="abcd" * 16,
                    doc_hash="abcdabcdabcdabcd",
                    size_bytes=1024,
                )
            ]
        return IngestionManagerSnapshot(
            collection_options=["demo"],
            active_collection=collection,
            documents=documents,
        )

    def ingest_uploaded_file(
        self,
        uploaded_file: Any,
        *,
        collection: str,
        force: bool = False,
        on_progress: Any | None = None,
    ) -> IngestionResult:
        self.ingest_calls.append(
            {
                "name": uploaded_file.name,
                "collection": collection,
                "force": force,
            }
        )
        if on_progress is not None:
            on_progress("load", 1, 3)
            on_progress("transform", 2, 3)
            on_progress("upsert", 3, 3)
        return IngestionResult(
            source_path="Q:/tmp/alpha.pdf",
            collection=collection,
            file_hash="hash-demo",
            skipped=False,
            document_id="doc-alpha",
            chunk_count=4,
            vector_ids=["chunk-1", "chunk-2"],
            image_count=1,
            bm25_terms=9,
            trace_id="trace-alpha",
        )

    def delete_document(self, *, source_path: str, collection: str) -> DeleteResult:
        self.delete_calls.append({"source_path": source_path, "collection": collection})
        self.deleted = True
        return DeleteResult(
            doc_id=source_path,
            source_path=source_path,
            collection=collection,
            chunks_deleted=3,
            bm25_deleted=3,
            images_deleted=1,
            integrity_deleted=1,
            file_hash="abcd" * 16,
            doc_hash="abcdabcdabcdabcd",
            fallback_used=False,
            fallback_reason=None,
        )


def test_ingestion_manager_service_stages_uploaded_pdf_and_cleans_temp_file(tmp_path: Path) -> None:
    """
    Given:
        一个注入 fake pipeline 的 `IngestionManagerService`，并把上传暂存目录指向测试临时目录。
    When:
        调用 `ingest_uploaded_file()` 上传一份 PDF，并传入页面级进度回调。
    Then:
        - service 应先把上传内容落成本地临时 PDF；
        - 再把该路径交给 pipeline.run(collection/force/on_progress)；
        - pipeline 返回后，临时文件应立即被清理，避免 Dashboard 上传目录残留垃圾文件。
    """
    fake_pipeline = _FakePipeline()
    service = IngestionManagerService(
        pipeline=fake_pipeline,  # type: ignore[arg-type]
        upload_root=tmp_path,
    )
    upload = _FakeUploadedFile("alpha.pdf", b"%PDF-1.4 demo")
    progress_events: list[tuple[str, int, int]] = []

    result = service.ingest_uploaded_file(
        upload,
        collection="demo",
        force=True,
        on_progress=lambda stage_name, current, total: progress_events.append((stage_name, current, total)),
    )

    assert result.collection == "demo"
    assert progress_events == [
        ("load", 1, 3),
        ("transform", 2, 3),
        ("upsert", 3, 3),
    ]
    assert len(fake_pipeline.calls) == 1
    staged_path = Path(fake_pipeline.calls[0]["source_path"])
    assert fake_pipeline.calls[0]["file_exists_during_call"] is True
    assert staged_path.exists() is False


def test_ingestion_manager_service_rejects_non_pdf_upload_before_running_pipeline(tmp_path: Path) -> None:
    """
    Given:
        一个文件名不是 `.pdf` 的上传对象。
    When:
        调用 `ingest_uploaded_file()`。
    Then:
        service 应在进入 pipeline 之前直接抛出 `ValueError`，
        避免把当前只支持 PDF 的 Dashboard 上传入口伪装成“支持任意文件”。
    """
    fake_pipeline = _FakePipeline()
    service = IngestionManagerService(
        pipeline=fake_pipeline,  # type: ignore[arg-type]
        upload_root=tmp_path,
    )

    try:
        service.ingest_uploaded_file(_FakeUploadedFile("notes.txt", b"hello"), collection="demo")
    except ValueError as exc:
        assert "PDF" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-PDF upload")

    assert fake_pipeline.calls == []


def test_ingestion_manager_render_triggers_ingest_delete_and_progress_updates() -> None:
    """
    Given:
        一个会返回固定文档列表、可记录 ingest/delete 调用的 fake service，
        以及一个预设了上传文件、collection、按钮点击结果的 fake Streamlit。
    When:
        调用 `render(manager_service=fake_service)` 渲染 G4 页面。
    Then:
        - 页面应调用 `ingest_uploaded_file()` 并把 collection/force 正确传下去；
        - 进度回调应推动进度条与状态文案更新；
        - 页面还应允许删除选中文档，并在删除后重新拉取快照刷新文档列表。
    """
    fake_streamlit = _FakeStreamlit()
    fake_service = _FakeManagerService()

    render(manager_service=fake_service, st_module=fake_streamlit)  # type: ignore[arg-type]

    assert fake_service.ingest_calls == [
        {"name": "alpha.pdf", "collection": "demo", "force": True}
    ]
    assert fake_service.delete_calls == [
        {"source_path": "memory://docs/existing.pdf", "collection": "demo"}
    ]
    assert any(message[0] == "success" and "摄取完成" in message[1] for message in fake_streamlit.messages)
    assert any(message[0] == "success" and "删除完成" in message[1] for message in fake_streamlit.messages)
    assert any(update[1] and "加载文档" in update[1] for update in fake_streamlit.progress_updates)
    assert fake_streamlit.placeholder_captions[-1] == "最近完成阶段：写入存储"
