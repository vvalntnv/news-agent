from typing import Protocol, List

from .value_objects import ScrapeInformation
from .entities import NewsItem, Article

type Host = str


class NewsSource(Protocol):
    """
    Protocol for a source that discovers news items (links).
    Example: RSS Feed, Web Scraper (Link Finder).
    """

    scraping_informations: list[ScrapeInformation]

    async def check_for_news(self) -> List[NewsItem]: ...


class ContentExtractor(Protocol):
    """
    Protocol for extracting full content from a news item.
    """

    scraping_informations: dict[Host, ScrapeInformation]

    async def extract(self, item: NewsItem) -> Article: ...


class ArticleRepository(Protocol):
    """
    Protocol for persisting articles.
    """

    async def save(self, article: Article) -> Article: ...

    async def get_by_url(self, url: str) -> Article | None: ...
