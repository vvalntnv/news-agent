from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import ModelMessage

from infrastructure.ai.agent import ProjectPydanticAgent

pytestmark = pytest.mark.anyio


def _history_tracker(messages: list[ModelMessage]) -> list[ModelMessage]:
    return messages


class _StreamedResponse:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def stream_text(self) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk


class _RunStreamContextManager:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def __aenter__(self) -> _StreamedResponse:
        return _StreamedResponse(chunks=self._chunks)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc_type
        del exc
        del traceback


def _build_project_agent(
    mocked_agent: PydanticAgent[object, str],
) -> ProjectPydanticAgent[str, object]:
    return ProjectPydanticAgent(
        agent=cast(PydanticAgent[object, str], mocked_agent),
        output_type=str,
        dependencies_type=object,
        tools=[],
        toolsets=[],
        history_tracker=_history_tracker,
    )


def test_add_dependency_sets_dependency_and_returns_self() -> None:
    mocked_agent = cast(PydanticAgent[object, str], SimpleNamespace(run=AsyncMock()))
    agent = _build_project_agent(mocked_agent=mocked_agent)

    dependency_payload = {"scope": "test"}
    returned_agent = agent.add_dependency(dependency_payload)

    assert returned_agent is agent
    assert agent.dependencies == dependency_payload


async def test_run_raises_when_dependencies_not_set() -> None:
    mocked_agent = cast(PydanticAgent[object, str], SimpleNamespace(run=AsyncMock()))
    agent = _build_project_agent(mocked_agent=mocked_agent)

    with pytest.raises(AssertionError, match="This class has no deps"):
        await agent.run("hello")


async def test_run_calls_underlying_agent_with_prompt_and_deps_and_returns_output() -> (
    None
):
    run_mock = AsyncMock(return_value=SimpleNamespace(output="mocked-reply"))
    mocked_agent = cast(PydanticAgent[object, str], SimpleNamespace(run=run_mock))
    agent = _build_project_agent(mocked_agent=mocked_agent)
    dependency_payload = {"request_id": "abc"}

    agent.add_dependency(dependency_payload)
    result = await agent.run("What happened?")

    assert result == "mocked-reply"
    run_mock.assert_awaited_once_with("What happened?", deps=dependency_payload)


async def test_run_accepts_falsy_dependency_values() -> None:
    run_mock = AsyncMock(return_value=SimpleNamespace(output="ok"))
    mocked_agent = cast(PydanticAgent[object, str], SimpleNamespace(run=run_mock))
    agent = _build_project_agent(mocked_agent=mocked_agent)
    empty_dependency_payload: dict[str, str] = {}

    agent.add_dependency(empty_dependency_payload)
    result = await agent.run("prompt")

    assert result == "ok"
    run_mock.assert_awaited_once_with("prompt", deps=empty_dependency_payload)


async def test_stream_yields_all_chunks_from_run_stream() -> None:
    run_stream_mock = MagicMock(
        return_value=_RunStreamContextManager(chunks=["A", "B", "C"])
    )
    mocked_agent = cast(
        PydanticAgent[object, str],
        SimpleNamespace(run=AsyncMock(), run_stream=run_stream_mock),
    )
    agent = _build_project_agent(mocked_agent=mocked_agent)
    dependency_payload = {"tenant": "internal"}

    agent.add_dependency(dependency_payload)
    chunks = [chunk async for chunk in agent.stream("stream me")]

    assert chunks == ["A", "B", "C"]
    run_stream_mock.assert_called_once_with("stream me", deps=dependency_payload)


async def test_stream_raises_when_dependencies_not_set() -> None:
    run_stream_mock = MagicMock(
        return_value=_RunStreamContextManager(chunks=["ignored"])
    )
    mocked_agent = cast(
        PydanticAgent[object, str],
        SimpleNamespace(run=AsyncMock(), run_stream=run_stream_mock),
    )
    agent = _build_project_agent(mocked_agent=mocked_agent)

    with pytest.raises(AssertionError, match="This class has no deps"):
        _ = [chunk async for chunk in agent.stream("hello")]
