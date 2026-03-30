"""ChunkRefiner 真实 LLM 集成测试（C5）。"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.settings import Settings, load_settings
from core.trace.trace_context import TraceContext
from core.types import Chunk
from ingestion.transform.chunk_refiner import ChunkRefiner

pytestmark = [pytest.mark.integration, pytest.mark.llm]

NOISY_PDF_CHUNK = """
==============================
Page 42 | Technical Documentation
==============================


Chapter 5: System Architecture

The   microservices   architecture  consists  of  several  key  components.

<!-- Internal note: Update diagram -->

<div class="important">
Each service communicates via REST API or message queues.
</div>




The main   components   are:
- Gateway   Service
- Authentication  Service
- Data   Processing   Service


==============================
Footer: Copyright 2024 Company | Confidential
==============================
""".strip()

EXPECTED_CLEAN_RESULT_KEYWORDS = [
    "Chapter 5",
    "System Architecture",
    "microservices",
    "REST API",
    "message queues",
    "Gateway Service",
    "Authentication Service",
]


@pytest.fixture
def sample_noisy_chunk() -> Chunk:
    """
    Given:
        一段模拟 PDF 抽取后的噪声文本。
    When:
        作为测试输入传给 ChunkRefiner。
    Then:
        返回结构完整、可重复使用的标准 Chunk 数据对象。
    """
    return Chunk(
        id="test_pdf_chunk_001",
        text=NOISY_PDF_CHUNK,
        metadata={
            "source": "technical_doc.pdf",
            "source_path": "technical_doc.pdf",
            "page": 42,
            "doc_type": "pdf",
        },
        start_offset=0,
        end_offset=len(NOISY_PDF_CHUNK),
        source_ref="doc_technical_2024",
    )


def _load_project_settings() -> Settings:
    return load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))


def _required_env_keys(provider: str) -> list[str]:
    mapping = {
        "openai": ["OPENAI_API_KEY", "LLM_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "azure": ["AZURE_API_KEY", "AZURE_OPENAI_API_KEY"],
        "ollama": ["OLLAMA_BASE_URL"],
    }
    return mapping.get(provider, [])


def _has_real_key(value: str | None) -> bool:
    text = str(value or "").strip()
    if not text:
        return False

    placeholders = ["your_", "<", ">", "***", "dummy", "example"]
    lowered = text.lower()
    return not any(token in lowered for token in placeholders)


def _ensure_llm_runtime_ready(settings: Settings) -> None:
    provider = settings.llm.provider.strip().lower()
    if not provider:
        pytest.skip("settings.llm.provider 为空，跳过真实 LLM 集成测试")

    if not _has_real_key(settings.llm.api_key):
        env_keys = _required_env_keys(provider)
        found = any(_has_real_key(os.getenv(key)) for key in env_keys)
        if not found:
            if env_keys:
                pytest.skip(
                    "llm.api_key 为空或占位符，且缺少可用环境变量 "
                    f"{', '.join(env_keys)}，跳过真实 LLM 集成测试"
                )
            pytest.skip("llm.api_key 为空或占位符，跳过真实 LLM 集成测试")

    if provider == "azure":
        endpoint = settings.llm.endpoint.strip()
        deployment = (settings.llm.deployment_name or settings.llm.model).strip()
        if not endpoint or not deployment:
            pytest.skip("Azure 配置缺少 endpoint/deployment_name，跳过真实 LLM 集成测试")


def _with_chunk_refiner_use_llm(settings: Settings, enabled: bool) -> Settings:
    timeout = float(settings.llm.timeout) if float(settings.llm.timeout) > 0 else 30.0
    llm_cfg = replace(settings.llm, timeout=max(timeout, 90.0))

    return replace(
        settings,
        llm=llm_cfg,
        ingestion=replace(
            settings.ingestion,
            chunk_refiner=replace(settings.ingestion.chunk_refiner, use_llm=enabled),
        ),
    )


def _noise_score(text: str) -> int:
    """噪声评分：值越大表示格式噪声越多。"""
    score = 0
    score += text.count("Page 42")
    score += text.count("====")
    score += text.count("<!--")
    score += text.count("<div")
    score += text.lower().count("footer:")
    score += len(re.findall(r"\n{3,}", text))
    score += len(re.findall(r"[ \t]{2,}", text))
    return score


def _run_llm_with_retry(refiner: ChunkRefiner, chunk: Chunk, trace: TraceContext) -> Chunk:
    """网络抖动时重试一次，减少远程调用波动导致的误判。"""
    output = refiner.transform([chunk], trace=trace)[0]
    if output.metadata.get("refined_by") == "llm":
        return output

    reason = str(output.metadata.get("refine_fallback_reason", ""))
    if reason.startswith("llm_error:"):
        output = refiner.transform([chunk], trace=trace)[0]
    return output


def test_chunk_refiner_real_llm_refines_text(sample_noisy_chunk: Chunk) -> None:
    """
    Given:
        已配置且可用的真实 LLM（含 provider 与 api_key）。
    When:
        对带噪声文本执行 `ChunkRefiner.transform()`。
    Then:
        应触发 LLM 路径并产出更干净文本，同时保留关键业务词。
    """
    settings = _with_chunk_refiner_use_llm(_load_project_settings(), enabled=True)
    _ensure_llm_runtime_ready(settings)

    refiner = ChunkRefiner(settings=settings)
    trace = TraceContext(trace_type="ingestion")
    chunk = sample_noisy_chunk

    output = _run_llm_with_retry(refiner=refiner, chunk=chunk, trace=trace)

    if output.metadata.get("refined_by") != "llm":
        reason = str(output.metadata.get("refine_fallback_reason", "unknown"))
        if reason.startswith("llm_error:"):
            pytest.skip(f"真实 LLM 网络调用不稳定（{reason}），跳过本次断言")

    assert output.text.strip()
    assert output.metadata.get("refined_by") == "llm"
    assert _noise_score(output.text) < _noise_score(chunk.text)

    preserved = sum(1 for kw in EXPECTED_CLEAN_RESULT_KEYWORDS if kw in output.text)
    assert preserved >= 4


def test_refinement_quality_comparison(sample_noisy_chunk: Chunk) -> None:
    """
    Given:
        同一份 `sample_noisy_chunk` 输入。
    When:
        分别执行规则模式与 LLM 模式的 refinement。
    Then:
        两种结果都应可用；LLM 模式通常具有更低噪声评分，并输出对比信息便于人工评审。
    """
    base_settings = _load_project_settings()
    _ensure_llm_runtime_ready(base_settings)

    settings_rule = _with_chunk_refiner_use_llm(base_settings, enabled=False)
    settings_llm = _with_chunk_refiner_use_llm(base_settings, enabled=True)

    rule_refiner = ChunkRefiner(settings=settings_rule)
    llm_refiner = ChunkRefiner(settings=settings_llm)

    rule_output = rule_refiner.transform([sample_noisy_chunk])[0]
    llm_output = _run_llm_with_retry(
        refiner=llm_refiner,
        chunk=sample_noisy_chunk,
        trace=TraceContext(trace_type="ingestion"),
    )

    assert rule_output.text.strip()
    assert llm_output.text.strip()
    assert rule_output.metadata.get("refined_by") == "rule"

    if llm_output.metadata.get("refined_by") != "llm":
        reason = str(llm_output.metadata.get("refine_fallback_reason", "unknown"))
        if reason.startswith("llm_error:"):
            pytest.skip(f"真实 LLM 网络调用不稳定（{reason}），跳过本次断言")

    assert llm_output.metadata.get("refined_by") == "llm"

    rule_score = _noise_score(rule_output.text)
    llm_score = _noise_score(llm_output.text)
    assert llm_score <= rule_score

    print("\n" + "=" * 72)
    print("Refinement Quality Comparison")
    print("=" * 72)
    print(f"Rule score: {rule_score}")
    print(f"LLM  score: {llm_score}")
    print("-" * 72)
    print("[Rule Output]")
    print(rule_output.text)
    print("-" * 72)
    print("[LLM Output]")
    print(llm_output.text)
    print("=" * 72 + "\n")


def test_chunk_refiner_invalid_model_graceful_fallback(sample_noisy_chunk: Chunk) -> None:
    """
    Given:
        在真实配置基础上故意设置无效模型名。
    When:
        执行 `transform()`。
    Then:
        应优雅降级到规则模式，不抛致命异常，并记录 fallback 原因。
    """
    settings = _with_chunk_refiner_use_llm(_load_project_settings(), enabled=True)
    _ensure_llm_runtime_ready(settings)

    bad = replace(settings, llm=replace(settings.llm, model="model-does-not-exist-for-fallback-test"))

    refiner = ChunkRefiner(settings=bad)
    output = refiner.transform([sample_noisy_chunk])[0]

    assert output.metadata.get("refined_by") == "rule"
    assert "refine_fallback_reason" in output.metadata


