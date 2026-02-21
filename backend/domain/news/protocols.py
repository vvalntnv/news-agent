from typing import Protocol, List

from infrastructure.database.models.raw_news_data.model import RawNewsData

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

    async def create_article(self, article: Article) -> Article: ...

    async def retrieve_article(self, url: str) -> Article | None: ...

    async def update_article(self, article: Article) -> Article: ...

    async def update_article_media_local_url(
        self, article_url: str, media_type: str, local_url: str
    ) -> None: ...

    async def article_exists(self, url: str) -> bool: ...
