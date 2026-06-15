"""RagasEvaluator：对接 Ragas 评估框架的适配层。"""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import replace
from collections.abc import Callable, Mapping
import importlib
import sys
import types
from typing import Any

from core.settings import Settings
from libs.evaluator.base_evaluator import BaseEvaluator

RagasLoader = Callable[[], tuple[Any, Any, Any, Any, Any, Any]]

_MAX_CONTEXT_CHARS = 2000
_MAX_ANSWER_CHARS = 2000
_MAX_GROUND_TRUTH_CHARS = 1200
_MAX_CONTEXTS_FOR_RAGAS = 3


class RagasEvaluator(BaseEvaluator):
    """Ragas 评估器适配实现。

    做什么：
    - 接收统一的评估样本列表；
    - 将样本转换成 Ragas 需要的 dataset 形状；
    - 调用 Ragas 返回标准化指标字典。

    为什么：
    - `03-tech-stack.md` 要求评估体系保持可插拔；
    - 因此这里要把第三方框架封装在适配层后面，避免上层直接依赖 Ragas 的 API 细节。

    关键权衡：
    - 构造阶段不立即 import `ragas`，而是在真正执行评估时懒加载；
      这样没有安装该依赖的环境仍可正常导入项目，其它 evaluator 也不会被拖垮。
    - 输出统一压平成普通 dict，避免把 Ragas 自己的结果对象泄漏到上层调用方。

    失败路径：
    - `ragas`/`datasets` 未安装时，抛出带安装提示的 `ImportError`；
    - 真实 Ragas 后端需要可用的 LLM API Key；缺失时抛出 `ValueError`，避免“看似启用但实际没打分”；
    - 输入样本缺失关键字段时，抛出 `ValueError`，明确指出是哪个样本有问题；
    - 第三方评估执行失败时，异常继续向上抛，避免悄悄吞掉真实问题。

    Args:
        settings: 项目强类型配置。真实运行时用于复用 `llm` 和 `embedding` 配置创建 Ragas 后端。
        ragas_loader: 可注入的 Ragas 运行时加载器，便于单元测试替换第三方依赖。
    """

    def __init__(self, settings: Settings | None = None, ragas_loader: RagasLoader | None = None) -> None:
        self.settings = settings
        self._ragas_loader = ragas_loader or self._load_ragas_runtime

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        """执行 Ragas 评估并返回标准化指标。

        Args:
            samples: 评估样本列表。每条样本至少需要：
                - `query`
                - `retrieved_chunks`
                - `generated_answer`
                - `ground_truth`
            trace: 预留给后续可观测扩展；当前不参与评估调用。

        Returns:
            dict[str, Any]: 标准化指标字典，至少包含：
                - `faithfulness`
                - `answer_relevancy`
                - `context_precision`
                - `total`
                - `details`

        Raises:
            ImportError: 当前环境缺少 `ragas` 依赖。
            ValueError: 样本缺失关键字段或字段 shape 非法。
        """
        _ = trace
        if not samples:
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "total": 0,
                "details": [],
            }

        (
            evaluate_fn,
            dataset_factory,
            llm_factory,
            instructor_base_cls,
            embedding_factory,
            metrics_factory,
        ) = self._ragas_loader()
        normalized_rows = [self._normalize_sample(sample=sample, index=index) for index, sample in enumerate(samples)]
        dataset = dataset_factory(normalized_rows)
        llm = self._build_ragas_llm(llm_factory, instructor_base_cls)
        embeddings = self._build_ragas_embeddings(embedding_factory)
        raw_result = evaluate_fn(
            dataset,
            metrics=metrics_factory(),
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=True,
            show_progress=False,
        )

        metrics = self._normalize_metrics(raw_result)
        metrics["total"] = len(normalized_rows)
        metrics["details"] = normalized_rows
        return metrics

    @staticmethod
    def _normalize_sample(*, sample: dict[str, Any], index: int) -> dict[str, Any]:
        """把统一样本结构转换成 Ragas 常用字段。

        这里显式做字段校验，而不是让第三方库在更深处报错，
        目的是把错误定位在我们自己的契约层，便于调用方快速修正数据。
        """
        if not isinstance(sample, dict):
            raise ValueError(f"sample[{index}] must be dict")

        required_keys = ("query", "retrieved_chunks", "generated_answer", "ground_truth")
        missing = [key for key in required_keys if key not in sample]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"sample[{index}] missing required keys: {joined}")

        query = sample.get("query")
        generated_answer = sample.get("generated_answer")
        ground_truth = sample.get("ground_truth")
        retrieved_chunks = sample.get("retrieved_chunks")

        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"sample[{index}].query must be non-empty string")
        if not isinstance(generated_answer, str):
            raise ValueError(f"sample[{index}].generated_answer must be string")
        if not isinstance(ground_truth, str):
            raise ValueError(f"sample[{index}].ground_truth must be string")
        if not isinstance(retrieved_chunks, list):
            raise ValueError(f"sample[{index}].retrieved_chunks must be list[str]")

        contexts: list[str] = []
        for chunk_index, item in enumerate(retrieved_chunks):
            if not isinstance(item, str):
                raise ValueError(
                    f"sample[{index}].retrieved_chunks[{chunk_index}] must be string"
                )
            stripped = item.strip()
            if stripped:
                # Ragas 会把 contexts/answer 拼进评估 Prompt；真实文档 chunk 可能很长。
                # 这里限制单项长度，避免评估模型因为超长输入输出 <think> 或截断 JSON。
                contexts.append(_truncate_for_ragas(stripped, _MAX_CONTEXT_CHARS))
            if len(contexts) >= _MAX_CONTEXTS_FOR_RAGAS:
                # context_precision 会按 context 逐项询问 LLM；限制数量能让 CLI/Dashboard 保持可运行。
                # retrieval 指标仍在 EvalRunner 用完整 Top-K 计算，这里只影响 Ragas 语义打分成本。
                break

        return {
            "question": query.strip(),
            "answer": _truncate_for_ragas(generated_answer, _MAX_ANSWER_CHARS),
            "ground_truth": _truncate_for_ragas(ground_truth, _MAX_GROUND_TRUTH_CHARS),
            "contexts": contexts,
        }

    @staticmethod
    def _normalize_metrics(raw_result: Any) -> dict[str, Any]:
        """把 Ragas 返回值压平成普通 dict。

        兼容两类常见形态：
        - `result.to_dict()`
        - 已经是 `dict`
        """
        if hasattr(raw_result, "to_dict") and callable(raw_result.to_dict):
            payload = raw_result.to_dict()
        elif hasattr(raw_result, "_repr_dict"):
            payload = dict(raw_result._repr_dict)
        elif hasattr(raw_result, "scores") and isinstance(raw_result.scores, list):
            payload = _mean_scores(raw_result.scores)
        elif isinstance(raw_result, Mapping):
            payload = dict(raw_result)
        else:
            try:
                payload = dict(raw_result)
            except Exception as exc:
                raise ValueError("ragas evaluate() must return dict-like result") from exc

        return {
            "faithfulness": float(payload.get("faithfulness", 0.0)),
            "answer_relevancy": float(payload.get("answer_relevancy", 0.0)),
            "context_precision": float(payload.get("context_precision", 0.0)),
        }

    def _build_ragas_llm(self, llm_factory: Any, instructor_base_cls: type) -> Any:
        """根据项目 `llm` 配置创建真实 Ragas LLM。

        做什么：
        - 从 `Settings.llm` 读取 provider/model/api_key/base_url/timeout/proxy；
        - 用 OpenAI SDK 构造 OpenAI-compatible client；
        - 返回一个项目内 Ragas LLM 包装器，供 faithfulness/context_precision 等指标真实调用。

        为什么：
        - 如果不显式传入 LLM，Ragas 会尝试使用自己的默认 OpenAI 配置；
          那会绕过本项目 `settings.yaml`，也会让用户很难判断到底哪个模型在计费。
        - 当前项目的 MiniMax/Qwen/OpenAI 都走 OpenAI-compatible 协议，复用 OpenAI SDK client 是最小且可维护的接入方式。
        - Ragas 0.4.3 默认通过 instructor 解析 JSON；部分 reasoning 模型会在 JSON 前输出 `<think>`，
          因此这里用项目包装器在“真实调用模型”后提取合法 JSON，保证评估链路真实可用。

        关键权衡：
        - 这里只支持 Ragas 可直接消费的 OpenAI-compatible 文本 LLM；
          Azure/Ollama 等 provider 后续可按同一方法扩展，但不能在这里伪装成已支持。
        - API Key 缺失时 fail-fast，而不是回退成假分数；这样能保证“Ragas 启用”代表真实打分。

        失败路径：
        - 未传 `settings`：抛 `ValueError`，提示通过 `EvaluatorFactory.create(settings)` 构造；
        - provider 不支持或 API Key 缺失：抛 `ValueError`；
        - OpenAI SDK 未安装：抛 `ImportError`，提示补依赖。
        """
        settings = self._require_settings()
        llm_settings = self._resolve_ragas_llm_settings(settings)
        provider = llm_settings.provider.strip().lower()
        if provider not in {"openai", "deepseek"}:
            raise ValueError(
                "RagasEvaluator currently requires an OpenAI-compatible llm provider "
                f"(got {llm_settings.provider!r})"
            )
        if not llm_settings.model.strip():
            raise ValueError("RagasEvaluator requires llm.model for real Ragas scoring")
        if not llm_settings.api_key.strip():
            raise ValueError(
                "RagasEvaluator requires llm.api_key. Set LLM_API_KEY or switch llm.profile "
                "to a configured OpenAI-compatible provider."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - 依赖缺失由环境决定
            raise ImportError("RagasEvaluator requires `openai`; install project dependencies") from exc

        client_kwargs: dict[str, Any] = {
            "api_key": llm_settings.api_key,
            "base_url": llm_settings.base_url.rstrip("/") or "https://api.openai.com/v1",
            "timeout": float(llm_settings.timeout),
            "max_retries": int(llm_settings.max_retries),
        }

        if llm_settings.proxy.strip():
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - openai 通常会带 httpx
                raise ImportError("RagasEvaluator proxy support requires `httpx`") from exc
            # OpenAI SDK 的代理需要通过 httpx client 注入；这里不写入环境变量，避免影响项目其它请求。
            client_kwargs["http_client"] = httpx.Client(proxy=llm_settings.proxy.strip())

        client = OpenAI(**client_kwargs)
        if "minimax" not in llm_settings.profile.lower() and "minimax" not in llm_settings.model.lower():
            # 非 reasoning/非 <think> 模型优先走 Ragas 官方 instructor 适配器；
            # 这是最接近上游的真实 Ragas 调用路径，兼容性通常最好。
            return llm_factory(
                model=llm_settings.model,
                provider="openai",
                client=client,
                max_tokens=4096,
            )

        return _ProjectRagasLLM(
            instructor_base_cls=instructor_base_cls,
            client=client,
            model=llm_settings.model,
            max_tokens=4096,
        )

    @staticmethod
    def _resolve_ragas_llm_settings(settings: Settings) -> Any:
        """解析 Ragas 专用 LLM 配置。

        做什么：
        - 默认复用 `settings.llm`；
        - 若 `evaluation.ragas.llm_profile` 非空，则从 `settings.llm.profiles` 中取指定 profile。

        为什么：
        - 主聊天模型可能偏向推理、长回答或带 `<think>`，不一定适合 Ragas 结构化 JSON 打分；
        - 评估模型独立配置后，业务查询和质量评估可以分别选择最合适的模型。
        """
        profile_name = settings.evaluation.ragas.llm_profile.strip()
        if not profile_name:
            return settings.llm

        selected = settings.llm.profiles.get(profile_name)
        if not isinstance(selected, dict):
            raise ValueError(
                f"Unknown evaluation.ragas.llm_profile={profile_name!r}; "
                f"available profiles: {sorted(settings.llm.profiles)}"
            )

        return replace(
            settings.llm,
            profile=profile_name,
            provider=str(selected.get("provider", settings.llm.provider)),
            model=str(selected.get("model", settings.llm.model)),
            api_key=str(selected.get("api_key", settings.llm.api_key)),
            base_url=str(selected.get("base_url", settings.llm.base_url)),
            proxy=str(selected.get("proxy", settings.llm.proxy)),
            endpoint=str(selected.get("endpoint", settings.llm.endpoint)),
            deployment_name=str(selected.get("deployment_name", settings.llm.deployment_name)),
            api_version=str(selected.get("api_version", settings.llm.api_version)),
        )

    def _build_ragas_embeddings(self, embedding_factory: Any) -> Any:
        """根据项目 `embedding` 配置创建真实 Ragas Embedding。

        做什么：
        - `huggingface_local` 映射到 Ragas 的 `huggingface` provider，并加载本地 sentence-transformers 模型；
        - `openai` 映射到 OpenAI-compatible embedding client；
        - 其它 provider 明确报错，避免静默使用 Ragas 默认 embedding。

        为什么：
        - Answer Relevancy 等 Ragas 指标需要 embedding；
        - 显式传入 embedding 能保证评估使用的模型与项目配置一致，便于复现实验结果。

        失败路径：
        - 本地模型路径不存在或 sentence-transformers 缺失时，由 Ragas/HuggingFace provider 抛出可见异常；
        - OpenAI embedding 缺 key 时抛 `ValueError`；
        - 未支持 provider 时抛 `ValueError`，提示后续需要扩展适配。
        """
        settings = self._require_settings()
        embedding_settings = settings.embedding
        provider = embedding_settings.provider.strip().lower()

        if provider == "huggingface_local":
            embedding = embedding_factory(
                provider="huggingface",
                model=embedding_settings.model,
                device=embedding_settings.device,
                normalize_embeddings=embedding_settings.normalize_embeddings,
                batch_size=embedding_settings.batch_size,
            )
            return _RagasEmbeddingCompat(embedding)

        if provider == "openai":
            if not embedding_settings.api_key.strip():
                raise ValueError("RagasEvaluator requires embedding.api_key for OpenAI embeddings")
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise ImportError("RagasEvaluator requires `openai`; install project dependencies") from exc

            embedding = embedding_factory(
                provider="openai",
                model=embedding_settings.model or "text-embedding-3-small",
                client=OpenAI(
                    api_key=embedding_settings.api_key,
                    base_url=embedding_settings.base_url.rstrip("/") or "https://api.openai.com/v1",
                    timeout=float(embedding_settings.timeout),
                ),
            )
            return _RagasEmbeddingCompat(embedding)

        raise ValueError(
            "RagasEvaluator currently supports embedding.provider in "
            "{'huggingface_local', 'openai'} "
            f"(got {embedding_settings.provider!r})"
        )

    def _require_settings(self) -> Settings:
        """确保真实 Ragas 后端有项目配置可用。"""
        if self.settings is None:
            raise ValueError(
                "RagasEvaluator requires Settings for real scoring; "
                "construct it via EvaluatorFactory.create(settings)"
            )
        if not isinstance(self.settings, Settings):
            raise ValueError(
                "RagasEvaluator requires a core.settings.Settings object for real scoring; "
                "load config with load_settings('config/settings.yaml') first"
            )
        return self.settings

    @staticmethod
    def _load_ragas_runtime() -> tuple[Any, Any, Any, Any, Any]:
        """按需加载 Ragas 运行时对象。

        为什么做成独立方法：
        - 便于单元测试替换；
        - 也把 ImportError 的解释逻辑集中到一处，避免散落在业务分支里。
        """
        try:
            _install_ragas_vertexai_compat()
            from datasets import Dataset
            from ragas import evaluate
            from ragas.embeddings.base import embedding_factory
            from ragas.llms import llm_factory
            from ragas.llms.base import InstructorBaseRagasLLM
            from ragas.metrics import answer_relevancy, context_precision, faithfulness
        except ImportError as exc:
            raise ImportError(
                "RagasEvaluator requires optional dependencies: install `ragas`, `datasets`, "
                "`langchain-openai`, and compatible langchain packages first "
                f"(root cause: {type(exc).__name__}: {exc})"
            ) from exc

        def _metrics_factory() -> list[Any]:
            # 每次 evaluate 都返回一组新列表，避免第三方 metric 对象在多次运行间残留状态。
            return [faithfulness, answer_relevancy, context_precision]

        return evaluate, Dataset.from_list, llm_factory, InstructorBaseRagasLLM, embedding_factory, _metrics_factory


class _ProjectRagasLLM:
    """让 Ragas 通过项目 LLM 配置进行真实结构化打分。

    做什么：
    - 兼容 Ragas `InstructorBaseRagasLLM` 的 `generate/agenerate` 调用形状；
    - 使用 OpenAI-compatible client 真实请求项目配置中的 LLM；
    - 从模型输出中提取 JSON，再交给 Ragas 提供的 Pydantic `response_model` 校验。

    为什么：
    - 当前项目默认 LLM 可能是 MiniMax/Qwen 这类 reasoning 模型，模型会把 `<think>` 文本和 JSON 一起返回；
    - Ragas 依赖结构化 JSON，直接使用 instructor 时容易因为 `<think>` 或额外解释文字解析失败；
    - 自定义包装器可以保留真实 LLM 调用，同时把输出清洗集中在评估适配层。

    关键权衡：
    - 这里没有“伪造分数”，所有指标仍由 Ragas metric 调度；
    - 包装器只负责把模型响应整理成 Ragas 可验证的 Pydantic 对象；
    - 如果模型完全没有返回合法 JSON，错误会继续抛出，Dashboard/CLI 会在 `backend_errors` 中看到真实失败原因。
    """

    is_async = False

    def __new__(cls, instructor_base_cls: type, *args: Any, **kwargs: Any) -> "_ProjectRagasLLM":
        # 动态继承 Ragas 的 InstructorBaseRagasLLM，避免模块导入期强依赖 Ragas。
        dynamic_cls = type(
            "ProjectRagasLLM",
            (cls, instructor_base_cls),
            {},
        )
        instance = object.__new__(dynamic_cls)
        return instance

    def __init__(self, instructor_base_cls: type, client: Any, model: str, max_tokens: int = 2048) -> None:
        _ = instructor_base_cls
        self.client = client
        self.model = model
        self.max_tokens = int(max_tokens)

    def generate(self, prompt: str, response_model: type) -> Any:
        """同步生成 Ragas 所需的 Pydantic 输出对象。

        Args:
            prompt: Ragas metric 生成的评估 Prompt。
            response_model: Ragas metric 对应的 Pydantic 输出模型。

        Returns:
            response_model 实例。

        Raises:
            ValueError: 模型返回空内容或无法提取合法 JSON。
        """
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": (
                    "Return exactly one valid JSON object instance for the target schema. "
                    "Do not return the schema itself. Do not include markdown, explanations, "
                    "or thinking traces."
                ),
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nTarget JSON schema:\n{schema}",
            },
        ]

        last_error: Exception | None = None
        for attempt in range(2):
            content = self._complete(messages)
            try:
                json_payload = _extract_json_object(content)
                return response_model.model_validate_json(json_payload)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                # 第二轮把失败输出交还给模型修正。这里仍是真实 LLM 调用，
                # 只是把“结构化输出纠错”集中封装，避免 Ragas 调用方散落重试逻辑。
                messages.append({"role": "assistant", "content": content[:4000]})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous response was not a valid instance of the target schema. "
                            "Return only one JSON object with the required fields. "
                            f"Validation error: {type(exc).__name__}: {exc}"
                        ),
                    }
                )

        raise ValueError("Ragas LLM could not produce JSON matching the expected schema") from last_error

    def _complete(self, messages: list[dict[str, str]]) -> str:
        """调用真实 OpenAI-compatible chat completions，并返回文本内容。"""
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.01,
            max_tokens=self.max_tokens,
        )
        content = str(completion.choices[0].message.content or "").strip()
        if not content:
            finish_reason = getattr(completion.choices[0], "finish_reason", "<unknown>")
            raise ValueError(f"Ragas LLM returned empty content (finish_reason={finish_reason})")
        return content

    async def agenerate(self, prompt: str, response_model: type) -> Any:
        """异步生成接口；Ragas 可在异步 metric 中调用。"""
        return await asyncio.to_thread(self.generate, prompt, response_model)


class _RagasEmbeddingCompat:
    """把 Ragas 新版 embedding provider 适配给旧指标接口。

    Ragas 0.4.3 的 `answer_relevancy` 内部仍会调用 `embed_query()`，
    但同版本 `embedding_factory('huggingface')` 返回的新 provider 只有
    `embed_text()` / `embed_texts()`。这个小适配器只补接口形状，不改变向量计算来源。
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def embed_query(self, text: str) -> list[float]:
        """兼容 LangChain/Ragas 旧接口：单条 query 向量化。"""
        if hasattr(self.inner, "embed_query"):
            return list(self.inner.embed_query(text))
        return list(self.inner.embed_text(text))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """兼容 LangChain/Ragas 旧接口：多文档向量化。"""
        if hasattr(self.inner, "embed_documents"):
            return [list(row) for row in self.inner.embed_documents(texts)]
        return [list(row) for row in self.inner.embed_texts(texts)]

    async def aembed_query(self, text: str) -> list[float]:
        """异步 query 向量化；优先使用底层异步实现。"""
        if hasattr(self.inner, "aembed_query"):
            return list(await self.inner.aembed_query(text))
        if hasattr(self.inner, "aembed_text"):
            return list(await self.inner.aembed_text(text))
        return await asyncio.to_thread(self.embed_query, text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """异步文档向量化；供 Ragas 其它指标扩展时复用。"""
        if hasattr(self.inner, "aembed_documents"):
            return [list(row) for row in await self.inner.aembed_documents(texts)]
        if hasattr(self.inner, "aembed_texts"):
            return [list(row) for row in await self.inner.aembed_texts(texts)]
        return await asyncio.to_thread(self.embed_documents, texts)


def _truncate_for_ragas(text: str, max_chars: int) -> str:
    """限制进入 Ragas Prompt 的文本长度，并保留截断提示。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated for Ragas evaluation]"


def _mean_scores(rows: list[dict[str, Any]]) -> dict[str, float]:
    """计算 Ragas scores 行列表的列均值，忽略 NaN/None。"""
    values_by_key: dict[str, list[float]] = {}
    for row in rows:
        for key, value in row.items():
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isnan(number):
                continue
            values_by_key.setdefault(key, []).append(number)

    return {
        key: sum(values) / len(values)
        for key, values in values_by_key.items()
        if values
    }


def _extract_json_object(text: str) -> str:
    """从 reasoning/markdown 混合输出中提取第一个合法 JSON object。

    关键逻辑：
    - 先移除 `<think>...</think>`，解决 reasoning 模型把思考过程写进 content 的问题；
    - 再从每个 `{` 开始尝试 `json.JSONDecoder.raw_decode`；
    - 找到第一个 dict 后重新序列化为严格 JSON 字符串，交给 Pydantic 校验。
    """
    cleaned = text
    while "<think>" in cleaned and "</think>" in cleaned:
        start = cleaned.find("<think>")
        end = cleaned.find("</think>", start) + len("</think>")
        cleaned = cleaned[:start] + cleaned[end:]

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=False)

    raise ValueError("Ragas LLM response did not contain a valid JSON object")


def _install_ragas_vertexai_compat() -> None:
    """为 Ragas 0.4.x 与新版 langchain-community 安装窄兼容 shim。

    做什么：
    - Ragas 0.4.3 在导入 `ragas.llms.base` 时仍会引用
      `langchain_community.chat_models.vertexai.ChatVertexAI`；
    - 新版 `langchain-community` 已移除这个旧模块路径；
    - 如果真实模块缺失，就动态注册一个同名模块和占位类，让 Ragas 完成导入。

    为什么：
    - 项目真实使用的是 OpenAI-compatible LLM，不会走 VertexAI；
    - 这个 shim 只修复“导入阶段旧路径不存在”的兼容问题，不替代 Ragas 的评估、LLM 调用或 embedding 逻辑。

    关键权衡：
    - 不修改 site-packages，避免污染用户环境；
    - 只在 RagasEvaluator 懒加载时生效，避免影响项目其它 LangChain 使用方。
    """
    module_name = "langchain_community.chat_models.vertexai"
    try:
        importlib.import_module(module_name)
        return
    except ModuleNotFoundError as exc:
        # 只处理目标旧路径缺失；如果是 langchain_community 内部其它依赖坏了，应继续暴露原始错误。
        if exc.name != module_name:
            raise

    shim = types.ModuleType(module_name)

    class ChatVertexAI:  # pragma: no cover - 仅用于满足 Ragas 未使用路径的 isinstance 列表
        """Ragas 导入兼容占位类；项目不使用 VertexAI 后端。"""

    shim.ChatVertexAI = ChatVertexAI
    sys.modules[module_name] = shim
