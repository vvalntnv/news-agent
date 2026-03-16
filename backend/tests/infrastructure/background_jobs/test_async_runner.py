import pytest

from infrastructure.background_jobs.async_runner import AsyncRunner


def test_run_awaitable_safely_without_running_loop() -> None:
    async_runner = AsyncRunner[int]()

    async def _build_value() -> int:
        return 7

    result = async_runner.run_awaitable_safely(_build_value)

    assert result == 7


@pytest.mark.anyio
async def test_run_awaitable_safely_with_running_loop() -> None:
    async_runner = AsyncRunner[str]()

    async def _build_value() -> str:
        return "ok"

    result = async_runner.run_awaitable_safely(_build_value)

    assert result == "ok"
