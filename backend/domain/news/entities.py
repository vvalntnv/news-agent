from pydantic import BaseModel, Field

from domain.news.value_objects import ArticleContent


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

    title: str
    content: ArticleContent  # maps to raw_text + quotes
    videos: list[str] = Field(default_factory=list)
    timestamp: str
    author: str
    source_url: str | None = None
