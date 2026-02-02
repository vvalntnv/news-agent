from abc import ABC, abstractmethod
from typing import List
import httpx

from news_sourcing.models import News
from .protocols import NewsSource


class ScraperNewsSource(ABC, NewsSource):
    """
    Abstract Base Class for HTML Scraper-based news sources.
    """

    def __init__(self, base_url: str):
        self.source_link = base_url
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    @abstractmethod
    async def check_for_news(self) -> List[News]:
        """
        Must implement logic to go to the main page and find news links.
        """
        pass

    async def close(self):
        await self.client.aclose()
