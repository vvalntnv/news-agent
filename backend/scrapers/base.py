from typing import List, Protocol
from ..models import RawNewsData


class NewsSiteScraper(Protocol):
    """
    Protocol that all news site scrapers must implement.
    """

    async def check_for_news(self) -> List[str]:
        """
        Checks for new news on the website.
        
        Returns:
            List[str]: A list of titles or unique identifiers (urls) of the news found.
        """
        ...

    async def extract_data(self, urls: List[str]) -> List[RawNewsData]:
        """
        Extracts data from the specified news URLs.
        
        Args:
            urls (List[str]): List of URLs to scrape.
            
        Returns:
            List[str]: A list of RawNewsData objects containing the scraped content.
        """
        ...
