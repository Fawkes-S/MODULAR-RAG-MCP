"""QueryProcessor：查询预处理（D1）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.settings import Settings

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", flags=re.UNICODE)
_INLINE_FILTER_PATTERN = re.compile(
    r"\b(?P<key>collection|doc_type|doctype|language|source)\s*[:=]\s*(?P<value>[^\s,;]+)",
    flags=re.IGNORECASE,
)
_FILTER_KEY_ALIAS = {"doctype": "doc_type"}


@dataclass(frozen=True)
class ProcessedQuery:
    """查询预处理输出契约。

    Attributes:
        original_query: 原始查询文本（去除首尾空白）。
        normalized_query: 归一化查询文本（压缩多余空白）。
        keywords: 稀疏检索可直接消费的关键词列表（去重、保序）。
        filters: 通用过滤条件字典；D1 阶段允许为空。
    """

    original_query: str
    normalized_query: str
    keywords: list[str]
    filters: dict[str, Any]


class QueryProcessor:
    """查询预处理器，负责关键词提取与过滤条件结构化解析。

    做什么：
    - 对输入 query 做空白归一化、内联 filter 解析与词元提取。
    - 产出稳定的 `ProcessedQuery`，供 D2/D3/D5 的检索链路复用。
    - 在关键词全部被停用词过滤时提供回退策略，保证关键词非空。

    为什么：
    - D1 的目标是先把“查询前处理契约”稳定下来，后续 Dense/Sparse/Fusion 模块都围绕该契约实现。
    - 将 filter 结构提前抽离，便于 D5 在同一入口统一处理 pre-filter/post-filter 逻辑。

    关键权衡：
    - 当前采用“规则分词 + 轻量停用词”而非引入额外 NLP 依赖，优先保证可控和可测试。
    - filters 解析仅覆盖通用键（collection/doc_type/language/source）；
      复杂语法留给后续阶段迭代，避免 D1 过度设计。

    失败路径：
    - query 为空或非字符串：抛出 `ValueError`，避免把无效输入传递到检索后端。
    - `filters` 参数不是 dict：抛出 `ValueError`，防止过滤条件 shape 漂移。
    """

    _DEFAULT_STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "for",
        "how",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "了",
        "和",
        "在",
        "如何",
        "怎么",
        "是",
        "的",
    }

    def __init__(self, settings: Settings, stopwords: set[str] | None = None) -> None:
        """初始化查询预处理器。

        做什么：
        - 校验并保存全局 `Settings`。
        - 构建停用词集合（全部转小写并去空白），供关键词提取阶段复用。

        为什么：
        - 在构造阶段完成停用词归一化，避免每次 `process()` 重复做同样清洗。

        关键权衡：
        - 默认停用词表保持轻量，优先保证规则可解释和可维护；
          若业务词库需要细化，可通过 `stopwords` 注入覆盖。

        失败路径：
        - `settings` 类型不正确时抛出 `TypeError`，阻止处理器在半初始化状态下运行。

        Args:
            settings: 全局配置对象。
            stopwords: 可选停用词集合；为空时使用默认集合。
        """
        if not isinstance(settings, Settings):
            raise TypeError("QueryProcessor requires Settings; call load_settings('config/settings.yaml') first")

        self.settings = settings
        self.stopwords = {
            token.strip().lower() for token in (stopwords or self._DEFAULT_STOPWORDS) if token.strip()
        }

    def process(self, query: str, filters: dict[str, Any] | None = None) -> ProcessedQuery:
        """处理查询并返回结构化结果。

        做什么：
        - 标准化输入 query（去首尾空白、压缩多空格）。
        - 解析 query 内联过滤条件并与外部 `filters` 合并。
        - 提取关键词；若全部被停用词过滤，走回退策略确保关键词非空。

        为什么：
        - D2/D3 依赖稳定的关键词输入，D5 依赖统一 filters 结构；
          因此在此入口一次性完成规范化，减少下游分支复杂度。

        关键权衡：
        - 当前仅做轻量规则解析，不引入复杂语义改写，优先保证可预测行为和低运行成本。

        失败路径：
        - 非法 query 或非法 filters 会直接抛错；
          调用方应在入口层捕获并返回用户可读错误。

        Args:
            query: 用户原始查询文本。
            filters: 调用方附加的过滤条件，优先级高于 query 内联 filters。

        Returns:
            ProcessedQuery: 供后续检索链路消费的标准化查询对象。
        """
        normalized_query = self._normalize_query(query)
        inline_filters, query_without_filters = self._extract_inline_filters(normalized_query)
        # 设计约定：调用方传入的 filters 优先级更高，用于显式覆盖 query 中的内联条件。
        merged_filters = self._merge_filters(inline_filters, filters)

        keywords = self._extract_keywords(query_without_filters)
        if not keywords:
            # 回退策略：即便停用词策略过严，也要保证稀疏检索拿到非空关键词输入。
            keywords = self._fallback_keywords(query_without_filters or normalized_query)

        return ProcessedQuery(
            original_query=query.strip(),
            normalized_query=normalized_query,
            keywords=keywords,
            filters=merged_filters,
        )

    @staticmethod
    def _normalize_query(query: str) -> str:
        """归一化 query 字符串，并执行 fail-fast 输入校验。"""
        if not isinstance(query, str):
            raise ValueError("query must be non-empty string")
        normalized = " ".join(query.strip().split())
        if not normalized:
            raise ValueError("query must be non-empty string")
        return normalized

    def _extract_inline_filters(self, query: str) -> tuple[dict[str, str], str]:
        """提取内联过滤条件，并返回“去除过滤表达式后”的查询文本。"""
        parsed_filters: dict[str, str] = {}
        for match in _INLINE_FILTER_PATTERN.finditer(query):
            raw_key = match.group("key").strip().lower()
            # 统一别名，降低上游输入格式差异对下游筛选逻辑的影响。
            key = _FILTER_KEY_ALIAS.get(raw_key, raw_key)
            value = match.group("value").strip()
            if value:
                parsed_filters[key] = value

        # 将内联过滤片段从查询语句中剔除，避免被误当成检索关键词。
        sanitized_query = _INLINE_FILTER_PATTERN.sub(" ", query)
        sanitized_query = " ".join(sanitized_query.split())
        return parsed_filters, sanitized_query

    def _extract_keywords(self, query: str) -> list[str]:
        """按“规则分词 + 停用词过滤 + 去重保序”提取关键词。"""
        keywords: list[str] = []
        seen: set[str] = set()

        for token in _TOKEN_PATTERN.findall(query):
            normalized = token.lower().strip("_")
            if not normalized:
                continue
            if normalized in self.stopwords:
                continue
            if normalized in seen:
                continue
            keywords.append(normalized)
            seen.add(normalized)

        return keywords

    @staticmethod
    def _fallback_keywords(query: str) -> list[str]:
        """当关键词被全部过滤时，回退为“原始词元去重”策略。

        该方法的目标不是提升语义质量，而是保证查询链路的可用性下限。
        """
        tokens = [token.lower().strip("_") for token in _TOKEN_PATTERN.findall(query) if token.strip("_")]
        if not tokens:
            return [query]
        return list(dict.fromkeys(tokens))

    def _merge_filters(
        self,
        inline_filters: dict[str, str],
        external_filters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """合并内联与外部过滤条件，外部 filters 优先。"""
        if external_filters is None:
            return dict(inline_filters)
        if not isinstance(external_filters, dict):
            raise ValueError("filters must be dict when provided")

        merged = dict(inline_filters)
        for raw_key, raw_value in external_filters.items():
            if raw_value is None:
                continue
            key = _FILTER_KEY_ALIAS.get(str(raw_key).strip().lower(), str(raw_key).strip().lower())
            if not key:
                continue
            # 外部条件覆盖内联条件：让调用方在编排层拥有最终决策权。
            merged[key] = raw_value
        return merged
