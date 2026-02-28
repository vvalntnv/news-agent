from __future__ import annotations

from collections.abc import Mapping
from typing import Awaitable, Protocol, runtime_checkable


@runtime_checkable
class Agent(Protocol):
    """Protocol describing an AI agent that produces textual responses."""

    async def respond(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> str:
        """Return a textual response to ``prompt`` using optional sampling hints."""
        ...


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
