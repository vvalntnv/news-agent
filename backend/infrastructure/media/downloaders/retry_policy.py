from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from random import uniform
from typing import Sequence


@dataclass(frozen=True)
class RetryPolicy:
    """Encapsulates retry tuning values for HTTP download jobs."""

    max_attempts: int
    base_backoff_seconds: float
    max_backoff_seconds: float
    jitter_ratio: float
    retryable_status_codes: Sequence[int]
    fallback_penalty_seconds: float

    def next_delay(self, attempt: int, retry_after_header: str | None = None) -> float:
        backoff = self._apply_jitter(self._compute_base_backoff(attempt))
        fallback = self._clamped_fallback_penalty_seconds()
        retry_after = self.parse_retry_after(retry_after_header)

        delay = max(backoff, fallback)
        if retry_after is not None:
            delay = max(retry_after, delay)

        return delay

    def _clamped_fallback_penalty_seconds(self) -> float:
        fallback = max(self.fallback_penalty_seconds, 0.0)
        return min(fallback, self.max_backoff_seconds)

    def _compute_base_backoff(self, attempt: int) -> float:
        exponent = max(attempt - 1, 0)
        delay = self.base_backoff_seconds * (2**exponent)
        return min(delay, self.max_backoff_seconds)

    def _apply_jitter(self, delay: float) -> float:
        if delay <= 0 or self.jitter_ratio <= 0:
            return delay

        jitter_range = delay * self.jitter_ratio
        jittered = delay + uniform(-jitter_range, jitter_range)
        return min(max(jittered, 0.0), self.max_backoff_seconds)

    @staticmethod
    def parse_retry_after(header_value: str | None) -> float | None:
        if not header_value:
            return None

        value = header_value.strip()
        if not value:
            return None

        if value.isdigit():
            return float(value)

        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return max(0.0, (parsed - now).total_seconds())
