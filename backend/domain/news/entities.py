from pydantic import BaseModel, Field

from domain.news.value_objects import ArticleContent, Media


class NewsItem(BaseModel):
    """
    Represents a news item discovered from a source (e.g. RSS feed item or link on a page).
    It may not have the full content yet.
    """

    title: str
    url: str


class Article(BaseModel):
    """
    Represents a fully extracted news article.
    """

    article_id: int | None = None
    title: str
    content: ArticleContent  # maps to raw_text + quotes
    media: list[Media] = Field(default_factory=list)
    timestamp: str
    author: str
    article_url: str | None = None
