"""RagasEvaluator：对接 Ragas 评估框架的适配层。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from libs.evaluator.base_evaluator import BaseEvaluator

RagasLoader = Callable[[], tuple[Any, Any]]


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
    - `ragas` 未安装时，抛出带安装提示的 `ImportError`；
    - 输入样本缺失关键字段时，抛出 `ValueError`，明确指出是哪个样本有问题；
    - 第三方评估执行失败时，异常继续向上抛，避免悄悄吞掉真实问题。

    Args:
        ragas_loader: 可注入的 Ragas 运行时加载器，便于单元测试替换第三方依赖。
    """

    def __init__(self, ragas_loader: RagasLoader | None = None) -> None:
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

        evaluate_fn, dataset_factory = self._ragas_loader()
        normalized_rows = [self._normalize_sample(sample=sample, index=index) for index, sample in enumerate(samples)]
        dataset = dataset_factory(normalized_rows)
        raw_result = evaluate_fn(dataset)

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
                contexts.append(stripped)

        return {
            "question": query.strip(),
            "answer": generated_answer,
            "ground_truth": ground_truth,
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
        elif isinstance(raw_result, dict):
            payload = dict(raw_result)
        else:
            raise ValueError("ragas evaluate() must return dict-like result")

        return {
            "faithfulness": float(payload.get("faithfulness", 0.0)),
            "answer_relevancy": float(payload.get("answer_relevancy", 0.0)),
            "context_precision": float(payload.get("context_precision", 0.0)),
        }

    @staticmethod
    def _load_ragas_runtime() -> tuple[Any, Any]:
        """按需加载 Ragas 运行时对象。

        为什么做成独立方法：
        - 便于单元测试替换；
        - 也把 ImportError 的解释逻辑集中到一处，避免散落在业务分支里。
        """
        try:
            from datasets import Dataset
            from ragas import evaluate
        except ImportError as exc:
            raise ImportError(
                "RagasEvaluator requires optional dependencies: install `ragas` and `datasets` first"
            ) from exc

        return evaluate, Dataset.from_list
