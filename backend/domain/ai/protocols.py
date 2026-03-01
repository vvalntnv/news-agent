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
class Agent[O, D](Protocol):
    output_type: type[O]
    dependencies_type: type[D]

    tools: list[Tool]

    async def run(self, context: D) -> O:
        ...
