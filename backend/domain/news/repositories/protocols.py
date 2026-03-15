from typing import Protocol

from domain.common.repositories.protocols import RepositoryProtocol
from domain.news.entities import Article
from domain.news.repository_models.article import (
    ArticleRepositoryFilters,
    ArticleRepositoryUpdatePayload,
)


class ArticleRepositoryProtocol(
    RepositoryProtocol[
        Article,
        Article,
        ArticleRepositoryUpdatePayload,
        ArticleRepositoryFilters,
    ],
    Protocol,
):
    """Repository contract for article aggregate persistence."""

    async def get_by_url(self, url: str) -> Article | None: ...

    async def update_media_local_url(
        self,
        article_url: str,
        source_url: str,
        local_url: str,
    ) -> None: ...

    async def exists_by_url(self, url: str) -> bool: ...
