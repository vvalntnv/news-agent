from typing import List
import httpx
from urllib.parse import urlparse

from database.models import RawNewsData
from news_sourcing.models import News
from news_sourcing.models.models import ScrapeInformation
from .protocols import NewsExtractor, NewsSource


class ScraperNewsSource(NewsSource, NewsExtractor):
    """
    Abstract Base Class for HTML Scraper-based news sources.
    """

    def __init__(self, base_url: str, registered_scrapers: list[ScrapeInformation]):
        self.scraping_informations: dict[str, ScrapeInformation] = {}
        self.source_link = base_url
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=30.0,
        )

        for scraper in registered_scrapers:
            url_data = urlparse(scraper.scraping_url)
            hostname = url_data.hostname

            assert hostname is not None, "no hostname provided for scraping"

            self.scraping_informations.update({hostname: scraper})

    async def check_for_news(self) -> List[News]:
        """
        Must implement logic to go to the main page and find news links.
        """
        ...

    async def extract_news_data(self) -> list[RawNewsData]: ...

    async def close(self):
        await self.client.aclose()
