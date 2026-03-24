"""LLM Reranker implementation.

实现目标：
- 读取 `config/prompts/rerank.txt` 构造重排提示词；
- 调用 `BaseLLM.chat()` 返回结构化排序结果；
- 当 LLM 请求失败时抛出可识别的回退信号，供上层 fallback 使用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory
from libs.reranker.base_reranker import BaseReranker


class RerankFallbackSignal(RuntimeError):
    """重排失败回退信号。

    该异常用于向上层明确表达“本次可回退到 fusion 顺序”，
    而不是把请求异常误判为业务逻辑错误。
    """

    fallback = True

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class LLMReranker(BaseReranker):
    """基于 LLM 的候选重排器。"""

    provider_name = "llm"

    def __init__(
        self,
        llm: BaseLLM,
        prompt_template: str | None = None,
        prompt_path: str = "config/prompts/rerank.txt",
    ) -> None:
        """初始化 LLMReranker。

        Args:
            llm: 已配置好的 LLM 客户端实例。
            prompt_template: 可选，直接注入 prompt 模板（测试推荐）。
            prompt_path: 当未注入 `prompt_template` 时，从该路径加载模板。

        Raises:
            ValueError: `llm` 未传入，或模板为空时抛出。
        """
        if llm is None:
            raise ValueError("[llm_reranker] ValidationError: llm is required")

        self.llm = llm
        self.prompt_path = prompt_path
        self.prompt_template = prompt_template if prompt_template is not None else self._load_prompt(prompt_path)

        if not isinstance(self.prompt_template, str) or not self.prompt_template.strip():
            raise ValueError("[llm_reranker] ValidationError: prompt template must be non-empty")

    @classmethod
    def from_settings(cls, settings: Any) -> "LLMReranker":
        """根据全局配置创建 LLMReranker。

        配置读取策略：
        - LLM 客户端：由 `LLMFactory.create(settings)` 负责；
        - prompt_path：读取 `rerank.prompt_path`，缺失时使用默认值。
        """
        llm = LLMFactory.create(settings)
        prompt_path = cls._extract_prompt_path(settings)
        return cls(llm=llm, prompt_path=prompt_path)

    @staticmethod
    def _extract_prompt_path(settings: Any) -> str:
        if isinstance(settings, dict):
            rerank_cfg = settings.get("rerank")
            if isinstance(rerank_cfg, dict):
                path = rerank_cfg.get("prompt_path")
                if isinstance(path, str) and path.strip():
                    return path
            return "config/prompts/rerank.txt"

        rerank_obj = getattr(settings, "rerank", None)
        path = getattr(rerank_obj, "prompt_path", None)
        if isinstance(path, str) and path.strip():
            return path
        return "config/prompts/rerank.txt"

    @staticmethod
    def _load_prompt(prompt_path: str) -> str:
        """从文件读取 rerank prompt。"""
        path = Path(prompt_path)
        return path.read_text(encoding="utf-8")

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: Any | None = None,
    ) -> list[dict[str, Any]]:
        """调用 LLM 进行候选重排。

        Returns:
            list[dict[str, Any]]: 按 LLM 返回 `ranked_ids` 顺序重排后的候选列表。

        Raises:
            ValueError: 当响应 schema 非法（非结构化 JSON）时抛出可读错误。
            RerankFallbackSignal: 当 LLM 请求失败/超时时抛出回退信号。
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("[llm_reranker] ValidationError: query must be non-empty string")
        if not isinstance(candidates, list):
            raise ValueError("[llm_reranker] ValidationError: candidates must be list")
        if len(candidates) == 0:
            return []

        prompt = self._render_prompt(query=query, candidates=candidates)
        messages = [{"role": "user", "content": prompt}]

        try:
            raw = self.llm.chat(messages)
        except Exception as exc:
            raise RerankFallbackSignal(
                f"[llm_reranker] FallbackSignal: llm request failed: {type(exc).__name__}: {exc}"
            ) from exc

        payload = self._parse_json_payload(raw)
        ranked_ids = payload.get("ranked_ids")

        if not isinstance(ranked_ids, list) or any(not isinstance(x, str) or not x.strip() for x in ranked_ids):
            raise ValueError("[llm_reranker] ResponseSchemaError: expected {'ranked_ids': list[str]}")

        return self._reorder_candidates(candidates, ranked_ids)

    def _render_prompt(self, query: str, candidates: list[dict[str, Any]]) -> str:
        """构造最终发送给 LLM 的 prompt 文本。"""
        candidate_view = []
        for item in candidates:
            candidate_view.append(
                {
                    "id": str(item.get("id", "")),
                    "text": str(item.get("text", "")),
                    "score": item.get("score"),
                }
            )

        candidate_json = json.dumps(candidate_view, ensure_ascii=False)

        # 支持模板占位符；若模板没有占位符，则追加标准块，避免无声失败。
        if "{query}" in self.prompt_template or "{candidates}" in self.prompt_template:
            return self.prompt_template.format(query=query, candidates=candidate_json)

        return (
            f"{self.prompt_template.strip()}\n\n"
            f"Query:\n{query}\n\n"
            f"Candidates(JSON):\n{candidate_json}\n\n"
            "请仅返回 JSON：{'ranked_ids': ['id1', 'id2']}"
        )

    def _parse_json_payload(self, raw: str) -> dict[str, Any]:
        """解析 LLM 文本输出，提取 JSON 对象。"""
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("[llm_reranker] ResponseSchemaError: empty response")

        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                text = "\n".join(lines[1:-1]).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("[llm_reranker] ResponseSchemaError: response is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise ValueError("[llm_reranker] ResponseSchemaError: response JSON must be object")
        return payload

    @staticmethod
    def _reorder_candidates(
        candidates: list[dict[str, Any]],
        ranked_ids: list[str],
    ) -> list[dict[str, Any]]:
        """按 `ranked_ids` 重排；未命中的候选保留原相对顺序并放在尾部。"""
        id_to_pos: dict[str, int] = {}
        for idx, item_id in enumerate(ranked_ids):
            id_to_pos.setdefault(item_id, idx)

        indexed = list(enumerate(candidates))
        indexed.sort(
            key=lambda pair: (
                id_to_pos.get(str(pair[1].get("id", "")), 10**9),
                pair[0],
            )
        )
        return [item for _, item in indexed]
