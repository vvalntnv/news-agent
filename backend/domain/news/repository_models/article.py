from pydantic import BaseModel

from domain.news.value_objects import Media


class ArticleRepositoryFilters(BaseModel):
    article_id: int | None = None
    article_url: str | None = None


class ArticleRepositoryUpdatePayload(BaseModel):
    title: str | None = None
    raw_content: str | None = None
    quotes: list[str] | None = None
    media: list[Media] | None = None
    timestamp: str | None = None
    author: str | None = None
    article_url: str | None = None
