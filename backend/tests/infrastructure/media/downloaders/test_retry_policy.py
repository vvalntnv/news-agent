from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from infrastructure.media.downloaders.retry_policy import RetryPolicy


def test_parse_retry_after_numeric_value() -> None:
    assert RetryPolicy.parse_retry_after("7") == 7.0


def test_parse_retry_after_http_date() -> None:
    future = datetime.now(timezone.utc) + timedelta(seconds=4)
    header = format_datetime(future)

    parsed = RetryPolicy.parse_retry_after(header)
    assert parsed is not None
    assert 3.0 < parsed < 5.0


def test_next_delay_prefers_fallback_then_backoff() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        base_backoff_seconds=0.5,
        max_backoff_seconds=2.0,
        jitter_ratio=0.0,
        retryable_status_codes=(429,),
        fallback_penalty_seconds=0.75,
    )

    assert policy.next_delay(1, None) == 0.75
    assert policy.next_delay(2, None) == 1.0
