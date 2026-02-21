from __future__ import annotations

import asyncio

import httpx
import pytest

from infrastructure.media.downloaders.async_retry_job_pool import (
    AsyncRetryJobPool,
    RetryJob,
)
from infrastructure.media.downloaders.retry_policy import RetryPolicy
from tests.utils.http_errors import build_http_status_error


def _build_policy(**kwargs: object) -> RetryPolicy:
    parameters = {
        "max_attempts": 3,
        "base_backoff_seconds": 0.01,
        "max_backoff_seconds": 0.1,
        "jitter_ratio": 0.0,
        "retryable_status_codes": (429,),
        "fallback_penalty_seconds": 0.0,
    }
    parameters.update(kwargs)
    return RetryPolicy(**parameters)


async def test_pool_respects_concurrency_limit() -> None:
    active = 0
    max_active = 0
    lock = asyncio.Lock()

    def make_job(index: int) -> RetryJob[str]:
        async def attempt() -> str:
            nonlocal active, max_active
            async with lock:
                active += 1
                max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            async with lock:
                active -= 1
            return str(index)

        return RetryJob(id=str(index), attempt=attempt)

    jobs = [make_job(i) for i in range(4)]
    pool = AsyncRetryJobPool(jobs=jobs, policy=_build_policy(), concurrency=2)

    assert await pool.run() == ["0", "1", "2", "3"]
    assert max_active <= 2


async def test_pool_soft_halt_delays_new_attempts() -> None:
    loop = asyncio.get_running_loop()
    job1_attempts = 0
    job1_failure_time: float | None = None
    job1_failure_event = asyncio.Event()
    job2_start_time: float | None = None

    policy = _build_policy(fallback_penalty_seconds=0.2)

    async def job_one() -> str:
        nonlocal job1_attempts, job1_failure_time
        job1_attempts += 1
        if job1_attempts == 1:
            job1_failure_time = loop.time()
            job1_failure_event.set()
            raise build_http_status_error(429)
        return "first"

    async def job_two() -> str:
        nonlocal job2_start_time
        await job1_failure_event.wait()
        job2_start_time = loop.time()
        return "second"

    pool = AsyncRetryJobPool[str](
        jobs=[
            RetryJob(id="one", attempt=job_one),
            RetryJob(id="two", attempt=job_two),
        ],
        policy=policy,
        concurrency=2,
    )

    results = await pool.run()
    assert results == ["first", "second"]
    assert job1_attempts == 2
    assert job1_failure_time is not None
    assert job2_start_time is not None
    assert job2_start_time - job1_failure_time >= policy.next_delay(1, None) - 0.05


async def test_pool_retries_on_retryable_error() -> None:
    attempts = 0

    async def attempt() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise build_http_status_error(429)
        return "ok"

    pool = AsyncRetryJobPool(
        jobs=[RetryJob(id="retry", attempt=attempt)],
        policy=_build_policy(),
        concurrency=1,
    )

    assert await pool.run() == ["ok"]


async def test_pool_aborts_on_non_retryable_error() -> None:
    async def attempt() -> str:
        raise build_http_status_error(500)

    pool = AsyncRetryJobPool(
        jobs=[RetryJob(id="bad", attempt=attempt)],
        policy=_build_policy(),
        concurrency=1,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await pool.run()


async def test_pool_fails_after_exhausting_retries() -> None:
    async def attempt() -> str:
        raise build_http_status_error(429)

    pool = AsyncRetryJobPool(
        jobs=[RetryJob(id="loop", attempt=attempt)],
        policy=_build_policy(max_attempts=2),
        concurrency=1,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await pool.run()


async def test_pool_uses_retry_after_header_delay() -> None:
    attempts = 0
    retry_after_seconds = 1.0
    observed_delay: float | None = None

    policy = _build_policy(
        base_backoff_seconds=0.01,
        max_backoff_seconds=1.0,
        fallback_penalty_seconds=0.0,
    )

    async def on_retry(
        _job_id: str,
        _error: Exception,
        _attempt: int,
        delay: float,
    ) -> None:
        nonlocal observed_delay
        observed_delay = delay

    async def attempt() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise build_http_status_error(
                429,
                headers={"Retry-After": "1"},
            )
        return "ok"

    pool = AsyncRetryJobPool[str](
        jobs=[RetryJob(id="retry-after", attempt=attempt, on_retry=on_retry)],
        policy=policy,
        concurrency=1,
    )

    assert await pool.run() == ["ok"]
    assert observed_delay is not None
    assert observed_delay >= retry_after_seconds
    assert observed_delay == pytest.approx(retry_after_seconds, abs=0.05)
