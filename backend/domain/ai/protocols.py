from __future__ import annotations

from collections.abc import Mapping
from typing import AsyncIterable, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel

from domain.ai.configuration import AIConfiguration

type DependenciesType = BaseModel | str | int | dict


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
class Agent[T: BaseModel](Protocol):
    """Protocol describing an AI agent that produces textual responses."""

    output_model: T
    toolsets: list[Toolset]
    tools: list[Tool]
    config: AIConfiguration
    dependencies: BaseModel | str | int | dict

    async def stream_text(
        self,
        prompt: str,
    ) -> AsyncIterable[str]: ...

    async def stream(
        self,
        prompt: str,
    ) -> AsyncIterable[T]: ...

    async def respond(
        self,
        prompt: str,
    ) -> T: ...
