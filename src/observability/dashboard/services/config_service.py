"""Dashboard 配置读取服务。

这个服务专门负责把 `Settings` 转成适合 Dashboard 展示的“视图模型”：
- 页面层不需要理解底层配置结构；
- 组件卡片、运行状态等格式化逻辑集中在这里；
- 后续如果 `settings.yaml` 字段调整，优先只改这一层，避免页面渲染代码到处散落判断分支。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.settings import Settings, load_settings


@dataclass(frozen=True)
class ComponentCard:
    """Dashboard 上单张组件卡片的展示模型。"""

    title: str
    summary: str
    details: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeStatus:
    """Overview 页展示的运行状态快照。"""

    dashboard_port: int
    traces_dir: str
    trace_file: str
    trace_file_exists: bool
    last_trace_at: str
    auto_refresh: bool
    refresh_interval: int


class ConfigService:
    """读取 Settings 并组装 Dashboard 所需展示数据。

    做什么：
    - 统一读取 `config/settings.yaml`；
    - 把强类型 `Settings` 转成组件卡片与运行状态快照；
    - 负责路径解析与时间格式化，避免页面层出现与 UI 无关的样板代码。

    为什么：
    - Dashboard 页面更适合只关心“展示什么”，而不是“配置字段怎么拼接”；
    - 将这层抽出来后，后续 G3-G6 页面也能复用同一套配置与路径解析策略。

    关键权衡：
    - 这里返回的是面向展示的轻量 dataclass，而不是直接暴露原始 dict；
    - 这样页面更稳定，但也意味着字段变更时要同步调整服务和测试。
    """

    def __init__(self, settings_path: str | Path = "config/settings.yaml") -> None:
        self.settings_path = Path(settings_path)
        self._settings: Settings | None = None

    def load_settings(self) -> Settings:
        """加载并缓存 Settings，避免同一轮渲染重复读文件。"""
        if self._settings is None:
            self._settings = load_settings(str(self.settings_path))
        return self._settings

    def build_component_cards(self) -> list[ComponentCard]:
        """把当前组件配置整理成 Overview 卡片列表。"""
        settings = self.load_settings()
        return [
            ComponentCard(
                title="LLM",
                summary=self._join_non_empty(settings.llm.provider, settings.llm.model),
                details=(
                    f"profile: {settings.llm.profile or '-'}",
                    f"timeout: {settings.llm.timeout:.0f}s",
                    f"retries: {settings.llm.max_retries}",
                ),
            ),
            ComponentCard(
                title="Embedding",
                summary=self._join_non_empty(settings.embedding.provider, settings.embedding.model or "(auto)"),
                details=(
                    f"batch_size: {settings.embedding.batch_size}",
                    f"device: {settings.embedding.device}",
                    f"normalize: {settings.embedding.normalize_embeddings}",
                ),
            ),
            ComponentCard(
                title="Splitter",
                summary=settings.ingestion.splitter,
                details=(
                    f"chunk_size: {settings.ingestion.chunk_size}",
                    f"chunk_overlap: {settings.ingestion.chunk_overlap}",
                    f"batch_size: {settings.ingestion.batch_size}",
                ),
            ),
            ComponentCard(
                title="Reranker",
                summary=settings.rerank.provider,
                details=(
                    f"enabled: {settings.rerank.enabled}",
                    f"top_m: {settings.rerank.top_m}",
                    f"timeout: {settings.rerank.timeout:.1f}s",
                ),
            ),
            ComponentCard(
                title="Evaluator",
                summary=settings.evaluation.provider,
                details=(
                    f"enabled: {settings.evaluation.enabled}",
                    f"trace_file: {settings.observability.trace_file}",
                ),
            ),
        ]

    def build_runtime_status(self) -> RuntimeStatus:
        """生成 Dashboard 自身的运行状态快照。"""
        settings = self.load_settings()
        trace_file = self._resolve_project_path(settings.observability.trace_file)
        last_trace_at = "-"
        if trace_file.exists():
            # Overview 只需要“最近有无写入”的健康信号，因此读取 mtime 即可。
            last_trace_at = datetime.fromtimestamp(trace_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        return RuntimeStatus(
            dashboard_port=settings.dashboard.port,
            traces_dir=str(self._resolve_project_path(settings.dashboard.traces_dir)),
            trace_file=str(trace_file),
            trace_file_exists=trace_file.exists(),
            last_trace_at=last_trace_at,
            auto_refresh=settings.dashboard.auto_refresh,
            refresh_interval=settings.dashboard.refresh_interval,
        )

    def _resolve_project_path(self, raw_path: str) -> Path:
        """将相对路径解析到当前 settings 所在项目根目录。"""
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.settings_path.resolve().parent.parent / path).resolve()

    @staticmethod
    def _join_non_empty(left: str, right: str) -> str:
        """把常用的 provider/model 展示为紧凑摘要。"""
        parts = [part.strip() for part in (left, right) if str(part).strip()]
        return " / ".join(parts) if parts else "-"
