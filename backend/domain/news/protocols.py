from typing import Protocol

from domain.news.entities import NewsItem, Article
from domain.news.value_objects import ScrapeInformation

type Host = str


class NewsSource(Protocol):
    """
    Protocol for a source that discovers news items (links).
    Example: RSS Feed, Web Scraper (Link Finder).
    """

    scraping_informations: list[ScrapeInformation]

    async def check_for_news(self) -> list[NewsItem]: ...


class ContentExtractor(Protocol):
    """
    Protocol for extracting full content from a news item.
    """

    scraping_informations: dict[Host, ScrapeInformation]

    async def extract(self, item: NewsItem) -> Article: ...
