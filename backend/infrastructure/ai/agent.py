from collections.abc import AsyncIterable
from typing import Self

from pydantic import BaseModel
from pydantic_ai import Agent as PydanticAgent

from core.loggers import get_ai_logger

from domain.ai.protocols import (
    Agent as AgentProtocol,
    HistoryTrackerFunc,
    Tool,
    Toolset,
)
from infrastructure.ai.event_logger import (
    AIEventStreamHandler,
    build_ai_event_stream_handler,
    consume_ai_run_events,
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
        self._ai_logger = get_ai_logger()
        self._ai_event_stream_handler: AIEventStreamHandler[D] = (
            build_ai_event_stream_handler(logger=self._ai_logger)
        )

    def add_dependency(self, dependency: D) -> Self:
        self.dependencies = dependency
        return self

    async def run(self, prompt: str) -> O:
        self._check_dependencies_ok()

        run_events = self._agent.run_stream_events(prompt, deps=self.dependencies)
        return await consume_ai_run_events(run_events, logger=self._ai_logger)

    async def stream(self, prompt: str) -> AsyncIterable[str]:
        self._check_dependencies_ok()

        async with self._agent.run_stream(
            prompt,
            deps=self.dependencies,
            event_stream_handler=self._ai_event_stream_handler,
        ) as streamed:
            async for chunk in streamed.stream_text():
                yield chunk

    def _check_dependencies_ok(self) -> None:
        assert hasattr(self, "dependencies"), "This class has no deps"

        if self.dependencies is None:
            raise AssertionError("The dependencies are not set!")
