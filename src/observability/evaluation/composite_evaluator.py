"""组合评估器：并行执行多个评估后端并汇总结果。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from libs.evaluator.base_evaluator import BaseEvaluator


class CompositeEvaluator(BaseEvaluator):
    """把多个评估器组合成一个统一入口。

    做什么：
    - 接收多个已经构造好的 `BaseEvaluator` 实例；
    - 对同一批样本并行调用各个评估器；
    - 把不同后端的指标压平成一个结果字典，方便后续 Dashboard 和脚本统一消费。

    为什么：
    - 技术规格要求 `evaluation.backends: [ragas, custom]` 这种配置可以一次跑多个后端；
    - 组合器把“多后端调度”从上层调用方剥离掉，避免 EvalRunner / Dashboard 自己管理线程和结果合并。

    关键权衡：
    - 这里选线程池而不是进程池，因为当前评估器大多是 I/O 或第三方库调用，线程实现更轻、更容易复用现有对象；
    - 合并结果时保留每个后端的原始输出到 `details_by_backend`，同时只把不冲突的顶层指标扁平化，避免静默覆盖。

    失败路径：
    - 如果没有传入任何评估器，构造阶段直接抛 `ValueError`，避免产生“什么都没评估但返回成功”的假象；
    - 如果某两个后端产出同名顶层指标但数值不同，会抛 `ValueError` 明确暴露命名冲突，而不是悄悄覆盖。
    """

    def __init__(self, evaluators: list[BaseEvaluator]) -> None:
        if not evaluators:
            raise ValueError("CompositeEvaluator requires at least one evaluator")
        self._evaluators = list(evaluators)

    def evaluate(self, samples: list[dict[str, Any]], trace: Any | None = None) -> dict[str, Any]:
        """并行执行所有评估器，并合并结构化结果。

        Args:
            samples: 统一评估样本列表。所有子评估器都会收到同一份输入。
            trace: 预留给后续评估链路观测；当前透明向下传递。

        Returns:
            dict[str, Any]:
                - 顶层平铺的聚合指标，例如 `hit_rate` / `mrr` / `faithfulness`
                - `total`: 样本总数
                - `details_by_backend`: 每个后端的完整原始结果
                - `details`: 兼容单评估器消费方的统一详情列表

        Raises:
            ValueError: 组合器为空，或不同后端产出同名冲突指标时抛出。
        """
        if len(self._evaluators) == 1:
            single_result = self._evaluators[0].evaluate(samples, trace=trace)
            return {
                **dict(single_result),
                "total": int(single_result.get("total", len(samples))),
                "details_by_backend": {self._backend_name(self._evaluators[0]): dict(single_result)},
            }

        backend_errors: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=len(self._evaluators)) as executor:
            futures = [
                (evaluator, executor.submit(evaluator.evaluate, samples, trace))
                for evaluator in self._evaluators
            ]

            successful_results: list[tuple[BaseEvaluator, dict[str, Any]]] = []
            for evaluator, future in futures:
                try:
                    # 只要还有其它 evaluator 可用，就不要让可选外部后端的依赖、
                    # 配置或网络错误拖垮整次评估；失败原因会进入 backend_errors，
                    # 调用方可以清楚看到 Ragas 并没有真实产出指标。
                    successful_results.append((evaluator, future.result()))
                except Exception as exc:  # noqa: BLE001
                    backend_errors[self._backend_name(evaluator)] = f"{type(exc).__name__}: {exc}"

            if not successful_results:
                error_summary = "; ".join(
                    f"{backend}={message}" for backend, message in sorted(backend_errors.items())
                )
                raise RuntimeError(
                    "CompositeEvaluator could not run any backend"
                    + (f" ({error_summary})" if error_summary else "")
                )

        merged: dict[str, Any] = {
            "total": len(samples),
            "details": [],
            "details_by_backend": {},
        }
        if backend_errors:
            merged["backend_errors"] = dict(backend_errors)

        used_backend_names: set[str] = set()

        for evaluator, result in successful_results:
            backend_name = self._allocate_backend_name(
                base_name=self._backend_name(evaluator),
                used_names=used_backend_names,
            )
            normalized_result = dict(result)
            merged["details_by_backend"][backend_name] = normalized_result

            # `details` 往往是后端私有结构，顶层只保留一个统一兼容字段，
            # 详细结果统一挂到 `details_by_backend`，防止 서로覆盖。
            backend_details = normalized_result.pop("details", None)
            if backend_details and not merged["details"]:
                merged["details"] = backend_details

            backend_total = normalized_result.pop("total", len(samples))
            if int(backend_total) > merged["total"]:
                merged["total"] = int(backend_total)

            for key, value in normalized_result.items():
                if key not in merged:
                    merged[key] = value
                    continue
                if merged[key] != value:
                    raise ValueError(
                        f"CompositeEvaluator metric conflict on '{key}' between backends"
                    )

        return merged

    @staticmethod
    def _backend_name(evaluator: BaseEvaluator) -> str:
        """用类名生成稳定后端名，方便展示和调试。"""
        class_name = evaluator.__class__.__name__
        return class_name.removesuffix("Evaluator").lower() or class_name.lower()

    @staticmethod
    def _allocate_backend_name(*, base_name: str, used_names: set[str]) -> str:
        """为 `details_by_backend` 分配不冲突的后端键名。"""
        if base_name not in used_names:
            used_names.add(base_name)
            return base_name

        suffix = 2
        while f"{base_name}_{suffix}" in used_names:
            suffix += 1

        allocated = f"{base_name}_{suffix}"
        used_names.add(allocated)
        return allocated
