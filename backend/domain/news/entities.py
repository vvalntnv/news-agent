from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """
    Represents a news item discovered from a source (e.g. RSS feed item or link on a page).
    It may not have the full content yet.
    """

    title: str | None = None
    url: str


class Article(BaseModel):
    """
    Represents a fully extracted news article.
    """

    title: str
    content: str  # maps to raw_text
    videos: list[str] = Field(default_factory=list)
    source_url: str | None = None
