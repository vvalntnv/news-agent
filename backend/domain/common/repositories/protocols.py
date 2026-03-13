from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel


class RepositoryProtocol[
    EntityT: BaseModel,
    CreateT: BaseModel,
    UpdateT: BaseModel,
    FilterT: BaseModel,
](Protocol):
    """Generic repository contract for persistence adapters."""

    async def create(self, payload: CreateT) -> EntityT: ...

    async def create_many(self, payloads: Sequence[CreateT]) -> list[EntityT]: ...

    async def update_one(
        self,
        filters: FilterT,
        payload: UpdateT,
    ) -> EntityT | None: ...

    async def update_many(self, filters: FilterT, payload: UpdateT) -> int: ...

    async def get(self, filters: FilterT) -> EntityT | None: ...

    async def get_many(
        self,
        filters: FilterT,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: tuple[str, ...] = (),
    ) -> list[EntityT]: ...
