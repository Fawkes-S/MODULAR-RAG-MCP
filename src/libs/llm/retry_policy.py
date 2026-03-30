"""LLM/Vision HTTP 重试策略工具。"""

from __future__ import annotations

import re
import socket
import time
from dataclasses import dataclass
from typing import Callable, TypeVar
from urllib.error import HTTPError, URLError

T = TypeVar("T")


class RetryableStatusError(RuntimeError):
    """表示服务端返回了可重试状态码（如 429/5xx）。"""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = int(status_code)
        self.message = str(message)
        super().__init__(f"status={self.status_code}: {self.message}")


@dataclass(frozen=True)
class RetryPolicy:
    """重试配置。

    Attributes:
        max_retries: 失败后最多重试次数（不含首轮请求）。
        initial_backoff_seconds: 首次重试前等待秒数。
        backoff_multiplier: 每轮退避倍数。
        max_backoff_seconds: 单轮最大等待秒数。
    """

    max_retries: int = 2
    initial_backoff_seconds: float = 0.25
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 2.0

    def normalized(self) -> "RetryPolicy":
        """返回边界修正后的策略，避免非法配置导致异常行为。"""
        return RetryPolicy(
            max_retries=max(0, int(self.max_retries)),
            initial_backoff_seconds=max(0.0, float(self.initial_backoff_seconds)),
            backoff_multiplier=max(1.0, float(self.backoff_multiplier)),
            max_backoff_seconds=max(0.0, float(self.max_backoff_seconds)),
        )

    @property
    def max_attempts(self) -> int:
        """总尝试次数（首轮 + 重试轮）。"""
        cfg = self.normalized()
        return 1 + cfg.max_retries

    def backoff_for_retry(self, retry_index: int) -> float:
        """计算第 retry_index 次重试应等待的秒数（从 1 开始计数）。"""
        cfg = self.normalized()
        delay = cfg.initial_backoff_seconds * (cfg.backoff_multiplier ** max(retry_index - 1, 0))
        return min(delay, cfg.max_backoff_seconds)


def summarize_exception(exc: BaseException, max_length: int = 120) -> str:
    """提取异常摘要，避免把冗长文本直接写入 metadata/日志。"""
    raw = str(exc).strip()
    if not raw:
        return ""

    first_line = raw.splitlines()[0]
    compact = re.sub(r"\s+", " ", first_line).strip()
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 1].rstrip()}…"


def _status_code_from_exception(exc: BaseException) -> int | None:
    code = getattr(exc, "status", None)
    if code is None:
        code = getattr(exc, "code", None)

    try:
        return int(code) if code is not None else None
    except Exception:
        return None


def is_retryable_exception(exc: BaseException) -> bool:
    """判断异常是否属于可重试类型。"""
    if isinstance(exc, RetryableStatusError):
        return exc.status_code == 429 or exc.status_code >= 500

    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True

    if isinstance(exc, HTTPError):
        code = int(exc.code)
        return code == 429 or code >= 500

    if isinstance(exc, URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return True

        reason_text = str(reason).lower()
        if "timed out" in reason_text or "timeout" in reason_text:
            return True

    code = _status_code_from_exception(exc)
    if code is not None and (code == 429 or code >= 500):
        return True

    lowered = str(exc).lower()
    if "timed out" in lowered or "timeout" in lowered:
        return True

    return False


def execute_with_retry(
    operation: Callable[[], T],
    *,
    policy: RetryPolicy | None = None,
    should_retry: Callable[[BaseException], bool] = is_retryable_exception,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """执行操作并按策略重试。"""
    cfg = (policy or RetryPolicy()).normalized()

    for attempt in range(1, cfg.max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt >= cfg.max_attempts or not should_retry(exc):
                raise

            delay = cfg.backoff_for_retry(retry_index=attempt)
            if delay > 0:
                sleep_fn(delay)

    raise RuntimeError("execute_with_retry reached an unexpected state")
