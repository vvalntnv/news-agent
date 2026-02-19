from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Sequence

import httpx

from infrastructure.media.downloaders.retry_policy import RetryPolicy

OnRetryHook = (
    Callable[[str, Exception, int, float], Awaitable[None]]
    | Callable[[str, Exception, int, float], None]
)


@dataclass(frozen=True)
class RetryJob[T]:
    id: str
    attempt: Callable[[], Awaitable[T]]
    on_retry: OnRetryHook | None = None


class AsyncRetryJobPool[T]:
    def __init__(
        self,
        jobs: Sequence[RetryJob[T]],
        policy: RetryPolicy,
        concurrency: int,
    ) -> None:
        if concurrency < 1:
            raise ValueError("Concurrency must be >= 1")

        self._jobs: list[RetryJob[T]] = list(jobs)
        self._policy = policy
        self._semaphore = asyncio.Semaphore(concurrency)
        self._pause_until: float = 0.0
        self._pause_lock = asyncio.Lock()

    async def run(self) -> list[T]:
        if not self._jobs:
            return []

        results: list[T | None] = [None] * len(self._jobs)

        try:
            async with asyncio.TaskGroup() as tg:
                for index, job in enumerate(self._jobs):
                    tg.create_task(self._run_job(job, index, results))
        except ExceptionGroup as exc_group:
            raise exc_group.exceptions[0] from None

        return self._finalize_results(results)

    async def _run_job(
        self,
        job: RetryJob[T],
        index: int,
        results: list[T | None],
    ) -> None:
        attempt = 1
        while True:
            await self._pause_execution_if_necessary()
            async with self._semaphore:
                if await self._is_pause_active():
                    continue

                result = None
                try:
                    result = await job.attempt()
                except Exception as exc:
                    await self._schedule_retry(job, attempt, exc)

            if result is None:
                attempt += 1
                continue

            results[index] = result
            return

    async def _is_pause_active(self) -> bool:
        now = asyncio.get_running_loop().time()
        async with self._pause_lock:
            return self._pause_until > now

    async def _schedule_retry(
        self,
        job: RetryJob[T],
        attempt: int,
        exc: Exception,
    ) -> T | None:
        retry_delay = self._retry_delay(exc, attempt)
        if retry_delay is None:
            raise

        await self._try_call_retry_hook(job, exc, attempt, retry_delay)
        await self._trigger_pause(retry_delay)
        return None

    def _retry_delay(self, exc: Exception, attempt: int) -> float | None:
        if attempt >= self._policy.max_attempts:
            return None

        if not isinstance(exc, httpx.HTTPStatusError):
            return None

        response = exc.response
        if response is None:
            return None

        if response.status_code not in self._policy.retryable_status_codes:
            return None

        retry_after = response.headers.get("Retry-After")
        return self._policy.next_delay(attempt, retry_after)

    async def _trigger_pause(self, delay: float) -> None:
        if delay <= 0:
            return

        now = asyncio.get_running_loop().time()
        async with self._pause_lock:
            self._pause_until = max(self._pause_until, now + delay)

    async def _pause_execution_if_necessary(self) -> None:
        while True:
            now = asyncio.get_running_loop().time()
            async with self._pause_lock:
                target = self._pause_until
            if target <= now:
                return

            await asyncio.sleep(target - now)

    async def _try_call_retry_hook(
        self,
        job: RetryJob[T],
        exc: Exception,
        attempt: int,
        delay: float,
    ) -> None:
        if job.on_retry is None:
            return

        hook_result = job.on_retry(job.id, exc, attempt, delay)
        if inspect.isawaitable(hook_result):
            await hook_result

    def _finalize_results(self, results: list[T | None]) -> list[T]:
        finalized: list[T] = []
        for index, value in enumerate(results):
            if value is None:
                raise RuntimeError(f"Missing result for job at index {index}")
            finalized.append(value)
        return finalized
