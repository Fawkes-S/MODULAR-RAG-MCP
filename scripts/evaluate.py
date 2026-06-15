"""H3 评估脚本入口：运行黄金测试集并输出核心指标。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.query_engine.hybrid_search import HybridSearch
from core.settings import load_settings
from libs.evaluator.evaluator_factory import EvaluatorFactory
from observability.evaluation.eval_runner import EvalRunner
from observability.logger import get_logger

LOGGER = get_logger("scripts.evaluate")


def _build_parser() -> argparse.ArgumentParser:
    """构建评估脚本参数解析器。"""
    parser = argparse.ArgumentParser(description="运行黄金测试集评估（H3）。")
    parser.add_argument(
        "--test-set",
        default="",
        help="黄金测试集路径；为空时使用 settings.yaml 中的 evaluation.golden_test_set。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 形式输出完整报告，便于后续脚本或 Dashboard 复用。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """脚本主入口：加载配置 -> 构建组件 -> 运行评估 -> 输出结果。"""
    args = _build_parser().parse_args(argv)
    settings = load_settings(str(PROJECT_ROOT / "config" / "settings.yaml"))

    test_set_path = args.test_set.strip() or settings.evaluation.golden_test_set
    hybrid_search = HybridSearch(settings=settings)
    evaluator = EvaluatorFactory.create(settings)
    runner = EvalRunner(
        settings=settings,
        hybrid_search=hybrid_search,
        evaluator=evaluator,
    )
    report = runner.run(test_set_path)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"[EVAL] test_set={report.test_set_path}")
    print(f"[EVAL] total={report.total} hit_rate={report.hit_rate:.4f} mrr={report.mrr:.4f}")

    evaluator_metrics = dict(report.evaluator_metrics)
    if evaluator_metrics:
        print("[EVAL] evaluator_metrics")
        for key, value in evaluator_metrics.items():
            if key in {"details", "details_by_backend"}:
                continue
            if isinstance(value, float):
                print(f"  - {key}: {value:.4f}")
            else:
                print(f"  - {key}: {value}")

    print("[EVAL] query_details")
    for index, detail in enumerate(report.details, start=1):
        status = "hit" if detail.hit else "miss"
        print(
            f"  {index}. [{status}] query={detail.query} "
            f"rank={detail.first_match_rank} "
            f"expected={list(detail.expected_chunk_ids) or list(detail.expected_sources)}"
        )
        if detail.error:
            print(f"     error={detail.error}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Evaluate command failed: %s", exc)
        raise SystemExit(1) from exc
