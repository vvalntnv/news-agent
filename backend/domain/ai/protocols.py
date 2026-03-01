from __future__ import annotations

from collections.abc import Mapping
from typing import AsyncIterable, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel

from domain.ai.configuration import AIConfiguration


@runtime_checkable
class Tool[T, D](Protocol):
    name: str
    description: str
    json_schema: Mapping[str, object]
    ctx: D | None

    def __call__(self, **kwargs: object) -> T | Awaitable[T]: ...


@runtime_checkable
class Toolset(Protocol):
    tools: list[Tool]
    name: str
    description: str


@runtime_checkable
class Agent[O: (BaseModel, str), D](Protocol):
    output_type: type[O]
    dependencies_type: type[D]

    tools: list[Tool]

    async def run(self, prompt: str) -> O: ...
    def stream(self, prompt: str) -> AsyncIterable[str]: ...


class AIFactory(Protocol):

    def create_agent[O: (BaseModel, str), D](
        self,
        config: AIConfiguration[O, D],
    ) -> Agent[O, D]: ...
