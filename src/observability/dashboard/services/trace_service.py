"""Dashboard Trace 数据读取服务。

这个服务负责把 `logs/traces.jsonl` 里的原始 JSON Lines 记录，
整理成 Dashboard 页面可以直接消费的稳定视图模型。

G5 当前先聚焦 Ingestion Trace，但实现上刻意保留了通用入口：
- 统一处理 trace 文件路径解析；
- 统一处理 JSON 行解析与坏行容错；
- 统一把阶段列表规整成“稳定主阶段 + 原始 payload”并返回给页面层。

这样 G6 做 Query Trace 时，可以直接复用同一个服务，
避免把文件读取和解析逻辑散落到多个页面文件里。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.settings import Settings, load_settings

_INGESTION_STAGE_ORDER = ("load", "split", "transform", "embed", "upsert")


@dataclass(frozen=True)
class TraceStageBreakdown:
    """单个稳定主阶段的聚合结果。"""

    stage_name: str
    elapsed_ms: float
    status: str
    method: str
    provider: str
    present: bool
    source_stages: tuple[str, ...]


@dataclass(frozen=True)
class DashboardTraceRecord:
    """Dashboard 层消费的一条 trace 记录。

    做什么：
    - 保留页面列表展示最常用的摘要字段；
    - 额外附带 `stage_breakdown` 与 `raw_payload`，便于详情页和后续页面复用。

    为什么：
    - 页面层只关心“按什么展示”，不应再自己翻原始 JSON 结构找字段；
    - 但完全丢掉原始 payload 又会让后续扩展成本变高，因此这里两者兼顾。
    """

    trace_id: str
    trace_type: str
    started_at: str
    finished_at: str | None
    total_elapsed_ms: float
    status: str
    source_path: str
    file_name: str
    collection: str
    stage_breakdown: tuple[TraceStageBreakdown, ...]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class TraceReadResult:
    """一次 trace 文件读取后的聚合结果。"""

    trace_file: str
    skipped_lines: int
    records: list[DashboardTraceRecord]


@dataclass(frozen=True)
class TraceRuntimeConfig:
    """Dashboard 展示 trace 时需要的运行配置。"""

    auto_refresh: bool
    refresh_interval: int


class TraceService:
    """读取并规整 Dashboard 所需的 Trace 数据。

    做什么：
    - 从 `config/settings.yaml` 读取 trace 文件路径与 Dashboard 刷新配置；
    - 逐行解析 `traces.jsonl`；
    - 过滤指定 `trace_type`，并把阶段数据整理成稳定主阶段视图。

    为什么：
    - JSON Lines 是“便于写入”的格式，不是“便于页面直接读”的格式；
    - 解析、容错、字段回退这些脏活集中在 service 层，页面代码才能保持简单。

    关键权衡：
    - 对坏行采取“跳过并计数”的降级策略，而不是整页报错；
      因为 trace 日志是可观测性数据，不应该因个别脏数据让 Dashboard 完全不可用。
    - 返回轻量 dataclass，而不是暴露未约束的 dict，减少页面层分支判断。

    失败路径：
    - `settings.yaml` 不存在或不合法时，仍然直接抛错；
      因为这属于系统基础配置问题，继续降级只会让页面进入更不透明的状态。
    """

    def __init__(self, settings_path: str | Path = "config/settings.yaml") -> None:
        self.settings_path = Path(settings_path)
        self._settings: Settings | None = None

    def load_traces(self, trace_type: str | None = None) -> TraceReadResult:
        """读取 trace 文件，并按需过滤 `trace_type`。

        Args:
            trace_type: 可选 trace 类型过滤，例如 `ingestion` / `query`。

        Returns:
            TraceReadResult: 包含 trace 文件路径、坏行计数与排序后的记录列表。
        """
        trace_file = self._resolve_trace_file()
        if not trace_file.exists():
            return TraceReadResult(trace_file=str(trace_file), skipped_lines=0, records=[])

        normalized_type = str(trace_type or "").strip().lower()
        records: list[DashboardTraceRecord] = []
        skipped_lines = 0

        for raw_line in trace_file.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue

            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                # 单条坏行不应拖垮整个 Dashboard；这里计数并跳过，便于页面提示。
                skipped_lines += 1
                continue

            if not isinstance(payload, dict):
                skipped_lines += 1
                continue

            record = self._build_trace_record(payload)
            if record is None:
                skipped_lines += 1
                continue

            if normalized_type and record.trace_type.lower() != normalized_type:
                continue
            records.append(record)

        records.sort(key=self._sort_key, reverse=True)
        return TraceReadResult(trace_file=str(trace_file), skipped_lines=skipped_lines, records=records)

    def get_runtime_config(self) -> TraceRuntimeConfig:
        """返回 Dashboard 追踪页面使用的刷新配置。"""
        settings = self._load_settings()
        return TraceRuntimeConfig(
            auto_refresh=bool(settings.dashboard.auto_refresh),
            refresh_interval=int(settings.dashboard.refresh_interval),
        )

    def _build_trace_record(self, payload: dict[str, Any]) -> DashboardTraceRecord | None:
        """把单条原始 payload 规整成页面可用记录。

        失败路径：
        - 缺少 `trace_id` 这类关键主键时返回 `None`，让调用方按“坏行”处理；
        - 其余非关键字段尽量回退为 `-` 或 `0.0`，保证旧 trace 也能被展示。
        """
        trace_id = str(payload.get("trace_id", "")).strip()
        if not trace_id:
            return None

        trace_type = str(payload.get("trace_type", "unknown")).strip() or "unknown"
        started_at = str(payload.get("started_at", payload.get("created_at", ""))).strip()
        finished_at_raw = payload.get("finished_at")
        finished_at = str(finished_at_raw).strip() if finished_at_raw is not None else None
        total_elapsed_ms = self._coerce_float(payload.get("total_elapsed_ms", 0.0))

        stages = payload.get("stages")
        stage_rows = stages if isinstance(stages, list) else []

        source_path = self._extract_context_value(payload=payload, stages=stage_rows, key="source_path")
        collection = self._extract_context_value(payload=payload, stages=stage_rows, key="collection")
        file_name = self._derive_file_name(source_path)
        stage_breakdown = self._build_ingestion_stage_breakdown(stage_rows)
        status = self._derive_trace_status(stage_rows=stage_rows, finished_at=finished_at)

        return DashboardTraceRecord(
            trace_id=trace_id,
            trace_type=trace_type,
            started_at=started_at,
            finished_at=finished_at,
            total_elapsed_ms=total_elapsed_ms,
            status=status,
            source_path=source_path,
            file_name=file_name,
            collection=collection,
            stage_breakdown=stage_breakdown,
            raw_payload=dict(payload),
        )

    def _build_ingestion_stage_breakdown(self, stages: list[Any]) -> tuple[TraceStageBreakdown, ...]:
        """把原始阶段列表聚合成 G5 需要的稳定主阶段。

        做什么：
        - 只抽取 `load/split/transform/embed/upsert`；
        - 对同名阶段做耗时求和；
        - 保留首个 `method/provider`，并记录来源细粒度阶段名。

        为什么：
        - `pipeline.*` 细粒度阶段适合排障，但不适合跨 trace 横向比较；
        - G5 页面需要的是稳定主阶段视图，而不是内部实现细节的完整镜像。
        """
        buckets: dict[str, dict[str, Any]] = {
            stage_name: {
                "elapsed_ms": 0.0,
                "status": "missing",
                "method": "",
                "provider": "",
                "present": False,
                "source_stages": [],
            }
            for stage_name in _INGESTION_STAGE_ORDER
        }

        for raw_stage in stages:
            if not isinstance(raw_stage, dict):
                continue

            stage_name = str(raw_stage.get("stage_name", "")).strip()
            if stage_name not in buckets:
                continue

            details = raw_stage.get("details")
            details_dict = details if isinstance(details, dict) else {}
            bucket = buckets[stage_name]
            bucket["present"] = True
            bucket["elapsed_ms"] += self._coerce_float(raw_stage.get("elapsed_ms", 0.0))

            if bucket["status"] != "error":
                stage_status = str(raw_stage.get("status", "ok")).strip().lower() or "ok"
                bucket["status"] = "error" if stage_status == "error" else "ok"

            if not bucket["method"]:
                bucket["method"] = str(details_dict.get("method", "")).strip()
            if not bucket["provider"]:
                bucket["provider"] = str(details_dict.get("provider", "")).strip()

            source_stage = str(details_dict.get("source_stage", stage_name)).strip() or stage_name
            if source_stage not in bucket["source_stages"]:
                bucket["source_stages"].append(source_stage)

        return tuple(
            TraceStageBreakdown(
                stage_name=stage_name,
                elapsed_ms=float(buckets[stage_name]["elapsed_ms"]),
                status=str(buckets[stage_name]["status"]),
                method=str(buckets[stage_name]["method"]),
                provider=str(buckets[stage_name]["provider"]),
                present=bool(buckets[stage_name]["present"]),
                source_stages=tuple(str(item) for item in buckets[stage_name]["source_stages"]),
            )
            for stage_name in _INGESTION_STAGE_ORDER
        )

    @staticmethod
    def _derive_trace_status(*, stage_rows: list[Any], finished_at: str | None) -> str:
        """根据阶段状态推导整条 trace 的状态。"""
        for raw_stage in stage_rows:
            if not isinstance(raw_stage, dict):
                continue
            if str(raw_stage.get("stage_name", "")).strip() == "pipeline.skip":
                return "skipped"
            stage_status = str(raw_stage.get("status", "")).strip().lower()
            if stage_status == "error":
                return "failed"
        return "success" if finished_at else "running"

    @staticmethod
    def _extract_context_value(*, payload: dict[str, Any], stages: list[Any], key: str) -> str:
        """从 root payload 或阶段 details 中兼容提取上下文字段。

        为什么要双路径提取：
        - 新旧 trace 版本可能把上下文放在不同位置；
        - 页面层不该关心“这批 trace 是哪一版打出来的”，这里统一兜底。
        """
        root_value = payload.get(key)
        if isinstance(root_value, str) and root_value.strip():
            return root_value.strip()

        for raw_stage in stages:
            if not isinstance(raw_stage, dict):
                continue
            details = raw_stage.get("details")
            if not isinstance(details, dict):
                continue
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return "-"

    @staticmethod
    def _derive_file_name(source_path: str) -> str:
        """从 `source_path` 提取更适合列表展示的文件名。"""
        text = str(source_path or "").strip()
        if not text or text == "-":
            return "-"
        return Path(text).name or text

    @staticmethod
    def _coerce_float(value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _sort_key(record: DashboardTraceRecord) -> tuple[float, str]:
        """按时间倒序排列 trace；时间缺失时退化到 trace_id。"""
        return (TraceService._timestamp_score(record.started_at, record.finished_at), record.trace_id)

    @staticmethod
    def _timestamp_score(started_at: str, finished_at: str | None) -> float:
        for raw_value in (started_at, finished_at or ""):
            if not raw_value:
                continue
            try:
                return datetime.fromisoformat(raw_value).timestamp()
            except ValueError:
                continue
        return 0.0

    def _resolve_trace_file(self) -> Path:
        settings = self._load_settings()
        return self._resolve_project_path(settings.observability.trace_file)

    def _load_settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings(str(self.settings_path))
        return self._settings

    def _resolve_project_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.settings_path.resolve().parent.parent / path).resolve()
