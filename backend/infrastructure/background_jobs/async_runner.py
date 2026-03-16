from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TypeVar


class AsyncRunner[R]:
    def run_awaitable_safely(
        self,
        awaitable_factory: Callable[[], Coroutine[object, object, R]],
    ) -> R:
        has_running_loop = self._detect_running_event_loop()
        if has_running_loop:
            return self._run_awaitable_in_new_thread(awaitable_factory)

        return asyncio.run(awaitable_factory())

    def _detect_running_event_loop(self) -> bool:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return False

        return True

    def _run_awaitable_in_new_thread(
        self,
        awaitable_factory: Callable[[], Coroutine[object, object, R]],
    ) -> R:
        with ThreadPoolExecutor(max_workers=1) as thread_pool:
            task: Future[R] = thread_pool.submit(
                self._run_awaitable_in_thread,
                awaitable_factory,
            )
            return task.result()

    def _run_awaitable_in_thread(
        self,
        awaitable_factory: Callable[[], Coroutine[object, object, R]],
    ) -> R:
        return asyncio.run(awaitable_factory())
