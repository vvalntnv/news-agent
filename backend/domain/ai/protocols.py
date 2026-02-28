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
class Agent[T: BaseModel](Protocol):
    """Protocol describing an AI agent that produces textual responses."""

    output_model: T
    toolsets: list[Toolset]
    tools: list[Tool]
    config: AIConfiguration

    async def stream(
        self,
        prompt: str,
    ) -> AsyncIterable[str]: ...

    async def respond(
        self,
        prompt: str,
    ) -> str:
        """Return a textual response to ``prompt`` using optional sampling hints."""
        ...

    async def get_structured_response(self, prompt: str) -> T: ...
