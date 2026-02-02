from typing import List, Protocol, runtime_checkable
from .models import News
from database.models import RawNewsData


@runtime_checkable
class NewsSource(Protocol):
    """
    Protocol that all news sources must implement.
    """

    source_link: str

    async def check_for_news(self) -> List[News]:
        """
        Checks for new news on the source.

        Returns:
            List[News]: A list of titles or unique identifiers (urls) of the news found.
        """
        ...


@runtime_checkable
class NewsExtractor(Protocol):
    """
    Protocol that extracts the News from the News class
    """

    news_site_domain: str

    async def extract_news_data(self) -> list[RawNewsData]:
        """
        Extracts the news raw data
        """
        ...
