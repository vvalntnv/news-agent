from typing import Protocol, List
from .entities import NewsItem, Article


class NewsSource(Protocol):
    """
    Protocol for a source that discovers news items (links).
    Example: RSS Feed, Web Scraper (Link Finder).
    """

    async def check_for_news(self) -> List[NewsItem]: ...


class ContentExtractor(Protocol):
    """
    Protocol for extracting full content from a news item.
    """

    async def extract(self, item: NewsItem) -> Article: ...


class ArticleRepository(Protocol):
    """
    Protocol for persisting articles.
    """

    async def save(self, article: Article) -> Article: ...

    async def get_by_url(self, url: str) -> Article | None: ...
