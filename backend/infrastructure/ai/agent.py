from collections.abc import AsyncIterable
from typing import Self

from pydantic import BaseModel
from pydantic_ai import Agent as PydanticAgent

from domain.ai.protocols import (
    Agent as AgentProtocol,
    HistoryTrackerFunc,
    Tool,
    Toolset,
)


class ProjectPydanticAgent[O: (BaseModel, str), D](AgentProtocol[O, D]):
    dependencies: D

    def __init__(
        self,
        agent: PydanticAgent[D, O],
        output_type: type[O],
        dependencies_type: type[D],
        tools: list[Tool],
        toolsets: list[Toolset],
        history_tracker: HistoryTrackerFunc,
    ) -> None:
        self._agent = agent
        self.output_type = output_type
        self.dependencies_type = dependencies_type
        self.tools = tools
        self.toolsets = toolsets
        self.history_tracker = history_tracker

    def add_dependency(self, dependency: D) -> Self:
        self.dependencies = dependency
        return self

    async def run(self, prompt: str) -> O:
        self._check_dependencies_ok()

        # TODO: Maybe here we need to track costs or usages?
        run_result = await self._agent.run(prompt, deps=self.dependencies)
        return run_result.output

    async def stream(self, prompt: str) -> AsyncIterable[str]:
        self._check_dependencies_ok()

        async with self._agent.run_stream(prompt, deps=self.dependencies) as streamed:
            async for chunk in streamed.stream_text():
                yield chunk

    def _check_dependencies_ok(self) -> None:
        assert hasattr(self, "dependencies"), "This class has no deps"

        if not self.dependencies:
            raise AssertionError("The dependencies are not set!")
