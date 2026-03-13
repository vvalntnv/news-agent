from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    AsyncIterable,
    Awaitable,
    Callable,
    Protocol,
    Self,
    runtime_checkable,
)

from pydantic import BaseModel
from pydantic_ai import ModelMessage

if TYPE_CHECKING:
    from domain.ai.configuration import AIConfiguration

type HistoryTrackerFunc = Callable[[list[ModelMessage]], list[ModelMessage]]


@runtime_checkable
class Tool[O, D](Protocol):
    name: str
    description: str
    ctx_type: type[D] | None
    __call__: Callable[..., O | Awaitable[O]]

    @property
    def json_schema(self) -> dict[str, object]: ...


@runtime_checkable
class Toolset(Protocol):
    tools: list[Tool]
    name: str
    description: str


@runtime_checkable
class Agent[O: (BaseModel, str), D](Protocol):
    output_type: type[O]
    dependencies_type: type[D]
    history_tracker: HistoryTrackerFunc

    tools: list[Tool]

    def add_dependency(self, dependency: D) -> Self: ...
    async def run(self, prompt: str) -> O: ...
    def stream(self, prompt: str) -> AsyncIterable[str]: ...


class AIFactory(Protocol):
    def create_agent[O: (BaseModel, str), D](
        self,
        config: AIConfiguration[O, D],
    ) -> Agent[O, D]: ...
