"""Dashboard 评估面板页面（H4）。

这个页面把 H3 已经实现的 `EvalRunner` 暴露到 Streamlit：
- 用户可以选择评估后端与 golden test set；
- 点击按钮后执行真实检索评估链路；
- 页面展示 retrieval 指标、Ragas/custom 等 evaluator 指标、逐 query 明细和本次会话历史。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from core.query_engine.hybrid_search import HybridSearch
from core.settings import Settings
from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.evaluator_factory import EvaluatorFactory
from observability.dashboard.pages._table_utils import render_wrapped_dataframe
from observability.dashboard.services.config_service import ConfigService
from observability.evaluation.eval_runner import EvalReport, EvalRunner

_SESSION_HISTORY_KEY = "evaluation_panel_history"
_CONFIG_BACKEND_OPTION = "<config>"
_DEFAULT_BACKEND_CANDIDATES = ("ragas", "custom", "ragas+custom")
_INTERNAL_METRIC_KEYS = {"details", "details_by_backend", "backend_errors"}


@dataclass(frozen=True)
class EvaluationPanelSnapshot:
    """评估面板渲染前的只读配置快照。

    做什么：
    - 收集当前 settings 中的评估配置；
    - 给页面层提供后端选择项、默认测试集路径、配置状态等展示信息。

    为什么：
    - 页面渲染代码应该关注“怎么展示”，不应该自己到处读取 settings 字段；
    - 把配置整理放在 service 层，可以让测试直接断言页面所需状态，而不是依赖 Streamlit。
    """

    evaluation_enabled: bool
    configured_backends: tuple[str, ...]
    configured_provider: str
    backend_options: list[str]
    backend_labels: dict[str, str]
    default_test_set_path: str
    retrieval_top_k: int
    ragas_llm_profile: str


class EvaluationPanelService:
    """Dashboard 评估面板的后端编排服务。

    做什么：
    - 读取 `config/settings.yaml` 中的评估配置；
    - 根据页面选择临时构造 evaluation provider/backends；
    - 创建 `HybridSearch`、`EvaluatorFactory` 和 `EvalRunner`，执行真实评估。

    为什么：
    - H4 的职责是把 H3 的评估闭环放到 Dashboard，而不是重新实现评估算法；
    - 因此页面服务必须复用现有 `EvalRunner`，确保 CLI 与 Dashboard 得到同一套指标定义。

    关键权衡：
    - 页面允许临时选择后端，但不会写回 settings.yaml，避免 UI 操作隐式修改项目配置；
    - 评估运行可能调用真实 Ragas/LLM，页面只在用户点击按钮后触发，避免打开页面就产生费用。

    失败路径：
    - settings 或 golden set 错误会继续向上抛出，让页面展示明确错误；
    - 若选择单独 `ragas` 且依赖/API Key 不可用，运行会失败；
    - 若选择配置默认 `ragas+custom`，CompositeEvaluator 会尽量保留 custom 结果并在 `backend_errors` 暴露 Ragas 错误。
    """

    def __init__(
        self,
        *,
        settings_path: str | Path = "config/settings.yaml",
        config_service: ConfigService | None = None,
        hybrid_search_factory: Callable[[Settings], Any] | None = None,
        evaluator_factory: Callable[[Settings], BaseEvaluator] | None = None,
        runner_factory: Callable[[Settings, Any, BaseEvaluator], EvalRunner] | None = None,
    ) -> None:
        self.config_service = config_service or ConfigService(settings_path)
        self._hybrid_search_factory = hybrid_search_factory
        self._evaluator_factory = evaluator_factory
        self._runner_factory = runner_factory

    def build_snapshot(self) -> EvaluationPanelSnapshot:
        """构建评估面板需要的配置快照。"""
        settings = self.config_service.load_settings()
        configured_backends = tuple(settings.evaluation.backends)
        configured_provider = settings.evaluation.provider.strip()
        backend_options, backend_labels = self._build_backend_options(settings)

        return EvaluationPanelSnapshot(
            evaluation_enabled=bool(settings.evaluation.enabled),
            configured_backends=configured_backends,
            configured_provider=configured_provider,
            backend_options=backend_options,
            backend_labels=backend_labels,
            default_test_set_path=str(self._resolve_project_path(settings.evaluation.golden_test_set)),
            retrieval_top_k=int(settings.retrieval.top_k),
            ragas_llm_profile=settings.evaluation.ragas.llm_profile,
        )

    def run_evaluation(self, *, test_set_path: str, backend_selection: str) -> EvalReport:
        """按页面选择执行一次完整评估。

        Args:
            test_set_path: golden test set 路径；支持绝对路径和相对项目根目录路径。
            backend_selection: 页面后端选项。`<config>` 表示使用 settings.yaml 原配置。

        Returns:
            EvalReport: H3 EvalRunner 产出的结构化评估报告。
        """
        base_settings = self.config_service.load_settings()
        run_settings = self._settings_for_backend_selection(base_settings, backend_selection)
        resolved_test_set = str(self._resolve_project_path(test_set_path or run_settings.evaluation.golden_test_set))

        hybrid_search = self._build_hybrid_search(run_settings)
        evaluator = self._build_evaluator(run_settings)
        runner = self._build_runner(run_settings, hybrid_search, evaluator)
        return runner.run(resolved_test_set)

    def _settings_for_backend_selection(self, settings: Settings, backend_selection: str) -> Settings:
        """根据页面选择构造本次运行专用 Settings。

        关键逻辑：
        - `<config>` 直接复用 settings.yaml；
        - `ragas+custom` 这类组合会转换成 `evaluation.backends`；
        - 单后端会同时设置 provider 和 backends，保证 EvaluatorFactory 路由明确。
        """
        selection = str(backend_selection or "").strip()
        if not selection or selection == _CONFIG_BACKEND_OPTION:
            return settings

        selected_backends = tuple(part.strip() for part in selection.split("+") if part.strip())
        if not selected_backends:
            return settings

        provider = selected_backends[0]
        evaluation = replace(
            settings.evaluation,
            provider=provider,
            backends=selected_backends,
        )
        return replace(settings, evaluation=evaluation)

    def _build_hybrid_search(self, settings: Settings) -> Any:
        """创建 HybridSearch；测试可注入 fake factory 避免触碰真实向量库。"""
        if self._hybrid_search_factory is not None:
            return self._hybrid_search_factory(settings)
        return HybridSearch(settings=settings)

    def _build_evaluator(self, settings: Settings) -> BaseEvaluator:
        """创建评估器；默认复用项目工厂，保持 provider 可插拔。"""
        if self._evaluator_factory is not None:
            return self._evaluator_factory(settings)
        return EvaluatorFactory.create(settings)

    def _build_runner(self, settings: Settings, hybrid_search: Any, evaluator: BaseEvaluator) -> EvalRunner:
        """创建 EvalRunner；测试可注入 fake runner 验证页面编排。"""
        if self._runner_factory is not None:
            return self._runner_factory(settings, hybrid_search, evaluator)
        return EvalRunner(settings=settings, hybrid_search=hybrid_search, evaluator=evaluator)

    def _build_backend_options(self, settings: Settings) -> tuple[list[str], dict[str, str]]:
        """生成页面后端选择项。

        这里不直接枚举 `EvaluatorFactory._registry`，避免页面依赖工厂内部实现；
        当前稳定展示内置候选，并把 settings 里已有的自定义后端补进去。
        """
        configured = tuple(settings.evaluation.backends) or (
            (settings.evaluation.provider.strip(),) if settings.evaluation.provider.strip() else ()
        )
        options: list[str] = [_CONFIG_BACKEND_OPTION]
        for candidate in [*configured, *_DEFAULT_BACKEND_CANDIDATES]:
            if candidate and candidate not in options:
                options.append(candidate)

        configured_label = ", ".join(configured) if configured else "-"
        labels = {_CONFIG_BACKEND_OPTION: f"使用配置默认 ({configured_label})"}
        labels.update({option: option for option in options if option != _CONFIG_BACKEND_OPTION})
        return options, labels

    def _resolve_project_path(self, raw_path: str | Path) -> Path:
        """把相对路径解析到项目根目录。

        失败路径：
        - 空路径会回退到 settings 中的 golden set；
        - 不检查文件是否存在，真正存在性校验交给 EvalRunner，让错误来源更清楚。
        """
        path = Path(str(raw_path).strip())
        if path.is_absolute():
            return path
        settings_path = self.config_service.settings_path.resolve()
        return (settings_path.parent.parent / path).resolve()


def render(
    evaluation_service: EvaluationPanelService | None = None,
    *,
    st_module: Any | None = None,
) -> None:
    """渲染 Dashboard 评估面板页面。"""
    if st_module is None:
        import streamlit as st
    else:
        st = st_module

    service = evaluation_service or EvaluationPanelService()
    snapshot = service.build_snapshot()

    st.title("评估面板")
    st.caption("运行 golden test set，查看 Hit Rate、MRR、Ragas/custom 指标和逐 query 明细。")
    _render_config_summary(st, snapshot)

    selected_backend = st.selectbox(
        "评估后端",
        options=snapshot.backend_options,
        index=0,
        format_func=lambda option: snapshot.backend_labels.get(option, option),
        help="默认使用 settings.yaml 中的 evaluation.backends；也可以临时只跑 custom 或 ragas。",
    )
    test_set_path = st.text_input(
        "Golden Test Set 路径",
        value=snapshot.default_test_set_path,
        help="支持绝对路径；相对路径会按项目根目录解析。",
    )

    if _selection_uses_ragas(selected_backend, snapshot):
        st.warning("当前选择包含 Ragas：运行时会调用真实评估 LLM/Embedding，耗时和费用取决于配置。")

    run_requested = st.button(
        "运行评估",
        type="primary",
        use_container_width=True,
    )

    active_report: EvalReport | None = None
    if run_requested:
        try:
            active_report = service.run_evaluation(
                test_set_path=test_set_path,
                backend_selection=selected_backend,
            )
        except Exception as exc:  # noqa: BLE001
            # Dashboard 的失败信息要直接暴露“哪个后端/测试集失败”，不能吞掉异常后只显示空结果。
            st.error(f"评估运行失败：{type(exc).__name__}: {exc}")
        else:
            st.success("评估运行完成。")
            _append_history(st, active_report)

    history = _get_history(st)
    if active_report is None and history:
        active_report = history[-1]

    if active_report is not None:
        _render_report(st, active_report)
    else:
        st.info("点击“运行评估”后，这里会展示本次评估指标和逐 query 明细。")

    _render_history(st, history)


def _render_config_summary(st: Any, snapshot: EvaluationPanelSnapshot) -> None:
    """展示当前评估配置摘要。"""
    st.subheader("评估配置")
    rows = [
        {
            "enabled": snapshot.evaluation_enabled,
            "configured_provider": snapshot.configured_provider or "-",
            "configured_backends": ", ".join(snapshot.configured_backends) if snapshot.configured_backends else "-",
            "golden_test_set": snapshot.default_test_set_path,
            "retrieval_top_k": snapshot.retrieval_top_k,
            "ragas_llm_profile": snapshot.ragas_llm_profile or "-",
        }
    ]
    render_wrapped_dataframe(st, rows)


def _render_report(st: Any, report: EvalReport) -> None:
    """展示一次评估报告的完整页面视图。"""
    st.subheader("聚合指标")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Test Cases", report.total)
    metric_columns[1].metric("Hit Rate", f"{report.hit_rate:.4f}")
    metric_columns[2].metric("MRR", f"{report.mrr:.4f}")
    metric_columns[3].metric("Generated At", report.generated_at)

    evaluator_metric_rows = _build_evaluator_metric_rows(report)
    if evaluator_metric_rows:
        st.markdown("**Evaluator 指标**")
        render_wrapped_dataframe(st, evaluator_metric_rows)

    backend_rows = _build_backend_rows(report)
    if backend_rows:
        st.markdown("**后端明细**")
        render_wrapped_dataframe(st, backend_rows)

    backend_error_rows = _build_backend_error_rows(report)
    if backend_error_rows:
        st.warning("部分评估后端运行失败；可用后端结果已保留。")
        render_wrapped_dataframe(st, backend_error_rows)

    st.subheader("逐 Query 明细")
    detail_rows = _build_detail_rows(report)
    if detail_rows:
        render_wrapped_dataframe(st, detail_rows)
    else:
        st.info("本次报告没有逐 query 明细。")


def _render_history(st: Any, history: list[EvalReport]) -> None:
    """展示本次 Dashboard 会话内的评估历史。"""
    st.subheader("本次会话评估历史")
    if not history:
        st.info("当前会话还没有历史评估结果。")
        return

    rows = [
        {
            "generated_at": item.generated_at,
            "test_set_path": item.test_set_path,
            "total": item.total,
            "hit_rate": round(item.hit_rate, 4),
            "mrr": round(item.mrr, 4),
            "backend_errors": ", ".join(_backend_errors(item).keys()) or "-",
        }
        for item in reversed(history)
    ]
    render_wrapped_dataframe(st, rows)


def _build_evaluator_metric_rows(report: EvalReport) -> list[dict[str, object]]:
    """把 evaluator 聚合指标整理成两列表格。"""
    rows: list[dict[str, object]] = []
    for key, value in report.evaluator_metrics.items():
        if key in _INTERNAL_METRIC_KEYS:
            continue
        rows.append({"metric": key, "value": _format_metric_value(value)})
    return rows


def _build_backend_rows(report: EvalReport) -> list[dict[str, object]]:
    """整理 `details_by_backend`，让用户能看清每个后端实际返回了什么。"""
    raw_backends = report.evaluator_metrics.get("details_by_backend")
    if not isinstance(raw_backends, dict):
        return []

    rows: list[dict[str, object]] = []
    for backend_name, payload in raw_backends.items():
        payload_dict = payload if isinstance(payload, dict) else {}
        metrics = {
            key: value
            for key, value in payload_dict.items()
            if key not in _INTERNAL_METRIC_KEYS
        }
        details = payload_dict.get("details")
        detail_count = len(details) if isinstance(details, list) else 0
        rows.append(
            {
                "backend": backend_name,
                "total": payload_dict.get("total", "-"),
                "detail_count": detail_count,
                "metrics": json.dumps(metrics, ensure_ascii=False, default=str),
            }
        )
    return rows


def _build_backend_error_rows(report: EvalReport) -> list[dict[str, object]]:
    """把 evaluator 后端错误整理成表格。"""
    return [
        {"backend": backend, "error": message}
        for backend, message in _backend_errors(report).items()
    ]


def _build_detail_rows(report: EvalReport) -> list[dict[str, object]]:
    """把 EvalRunner 逐 query 明细整理成 Dashboard 表格。"""
    return [
        {
            "query": detail.query,
            "hit": detail.hit,
            "first_match_rank": detail.first_match_rank if detail.first_match_rank is not None else "-",
            "reciprocal_rank": round(detail.reciprocal_rank, 4),
            "expected_chunk_ids": ", ".join(detail.expected_chunk_ids) or "-",
            "expected_sources": ", ".join(detail.expected_sources) or "-",
            "retrieved_chunk_ids": ", ".join(detail.retrieved_chunk_ids) or "-",
            "retrieved_sources": ", ".join(detail.retrieved_sources) or "-",
            "error": detail.error or "-",
        }
        for detail in report.details
    ]


def _backend_errors(report: EvalReport) -> dict[str, str]:
    """安全读取 evaluator_metrics.backend_errors。"""
    raw_errors = report.evaluator_metrics.get("backend_errors")
    if not isinstance(raw_errors, dict):
        return {}
    return {str(key): str(value) for key, value in raw_errors.items()}


def _format_metric_value(value: Any) -> object:
    """格式化指标值；float 保留四位，复杂对象转 JSON 文本。"""
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _selection_uses_ragas(selected_backend: str, snapshot: EvaluationPanelSnapshot) -> bool:
    """判断本次选择是否会触发 Ragas。

    `<config>` 需要回看 settings 中的实际 backends/provider；其它选项直接按字符串判断。
    """
    if selected_backend == _CONFIG_BACKEND_OPTION:
        configured = snapshot.configured_backends or (
            (snapshot.configured_provider,) if snapshot.configured_provider else ()
        )
        return any(item.strip().lower() == "ragas" for item in configured)
    return any(part.strip().lower() == "ragas" for part in selected_backend.split("+"))


def _get_history(st: Any) -> list[EvalReport]:
    """读取 Streamlit session_state 中的本次会话评估历史。"""
    session_state = getattr(st, "session_state", None)
    if session_state is None:
        return []
    if _SESSION_HISTORY_KEY not in session_state:
        session_state[_SESSION_HISTORY_KEY] = []
    return session_state[_SESSION_HISTORY_KEY]


def _append_history(st: Any, report: EvalReport, limit: int = 10) -> None:
    """把新报告追加到会话历史，并限制列表长度。"""
    history = _get_history(st)
    history.append(report)
    if len(history) > limit:
        del history[:-limit]
