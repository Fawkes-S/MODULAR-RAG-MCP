"""scripts/ingest.py 端到端行为测试（C15）。"""

from __future__ import annotations

import shutil
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import scripts.ingest as ingest_script


@dataclass
class _FakeResult:
    """脚本测试使用的摄取结果替身。"""

    skipped: bool
    file_hash: str = "fake_hash"
    chunk_count: int = 1
    vector_ids: list[str] = field(default_factory=lambda: ["v1"])
    image_count: int = 0
    bm25_terms: int = 0


class _FakePipeline:
    """可观测的 Pipeline 假实现：记录调用并按文件名可选触发失败。"""

    def __init__(self, fail_on_names: set[str] | None = None) -> None:
        self.fail_on_names = set(fail_on_names or set())
        self.calls: list[dict[str, object]] = []

    def run(self, source_path: str, collection: str = "default", *, force: bool = False):
        self.calls.append(
            {
                "source_path": source_path,
                "collection": collection,
                "force": force,
            }
        )

        if Path(source_path).name in self.fail_on_names:
            raise RuntimeError(f"simulated_failure:{Path(source_path).name}")

        return _FakeResult(skipped=False, file_hash=f"hash_{Path(source_path).stem}")


@pytest.fixture()
def sandbox_workspace() -> Path:
    """在项目目录内创建临时工作区，规避系统临时目录权限限制。"""
    root = PROJECT_ROOT / ".pytest_tmp" / f"c15_ingest_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write_fake_pdf(path: Path) -> None:
    """写入一个最小占位 PDF 文件头，满足路径与后缀约束。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n%fake-pdf\n")


def test_ingest_main_processes_directory_and_propagates_flags(
    sandbox_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        一个包含多层目录 PDF 的临时目录，以及一个可记录调用参数的 FakePipeline。
    When:
        执行 `main([--path <dir>, --collection test, --force])`。
    Then:
        - 返回码为 0；
        - 按稳定排序顺序处理所有 PDF；
        - 每次调用都正确透传 `collection=test` 与 `force=True`。
    """
    a_pdf = sandbox_workspace / "a.pdf"
    b_pdf = sandbox_workspace / "nested" / "b.pdf"
    c_pdf = sandbox_workspace / "nested" / "deep" / "c.pdf"
    _write_fake_pdf(a_pdf)
    _write_fake_pdf(b_pdf)
    _write_fake_pdf(c_pdf)

    fake_pipeline = _FakePipeline()
    monkeypatch.setattr(ingest_script, "_build_pipeline", lambda _settings: fake_pipeline)

    exit_code = ingest_script.main(
        [
            "--path",
            str(sandbox_workspace),
            "--collection",
            "test",
            "--force",
        ]
    )

    expected_order = [str(path.resolve()) for path in sorted([a_pdf, b_pdf, c_pdf])]
    actual_order = [str(call["source_path"]) for call in fake_pipeline.calls]

    assert exit_code == 0
    assert actual_order == expected_order
    assert all(call["collection"] == "test" for call in fake_pipeline.calls)
    assert all(call["force"] is True for call in fake_pipeline.calls)


def test_ingest_main_returns_non_zero_when_any_file_fails(
    sandbox_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Given:
        一个目录中有两个 PDF，其中一个文件名被配置为模拟失败。
    When:
        执行 `main([--path <dir>])`。
    Then:
        - 脚本继续处理剩余文件，不因单文件失败中断；
        - 最终返回码为 1，表示本批次存在失败项。
    """
    ok_pdf = sandbox_workspace / "ok.pdf"
    broken_pdf = sandbox_workspace / "broken.pdf"
    _write_fake_pdf(ok_pdf)
    _write_fake_pdf(broken_pdf)

    fake_pipeline = _FakePipeline(fail_on_names={"broken.pdf"})
    monkeypatch.setattr(ingest_script, "_build_pipeline", lambda _settings: fake_pipeline)

    exit_code = ingest_script.main(["--path", str(sandbox_workspace)])

    called_names = {Path(str(call["source_path"])).name for call in fake_pipeline.calls}

    assert called_names == {"ok.pdf", "broken.pdf"}
    assert exit_code == 1


def test_resolve_input_files_rejects_non_pdf_file(sandbox_workspace: Path) -> None:
    """
    Given:
        一个存在的非 PDF 文件路径（`.txt`）。
    When:
        调用 `_resolve_input_files(path)`。
    Then:
        抛出 `ValueError`，明确提示文件模式仅支持 PDF。
    """
    not_pdf = sandbox_workspace / "notes.txt"
    not_pdf.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="Only PDF file is supported"):
        ingest_script._resolve_input_files(str(not_pdf))
