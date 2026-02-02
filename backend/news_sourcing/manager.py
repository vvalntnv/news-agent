from typing import List
from .protocols import NewsSource
from ..database.models import RawNewsData


class NewsManager:
    """
    Manages multiple news sources and coordinates the collection of news.
    """

    def __init__(self):
        self.sources: List[NewsSource] = []

    def add_source(self, source: NewsSource):
        self.sources.append(source)

    async def collect_news(self) -> List[RawNewsData]:
        """
        Iterates over all sources, checks for new items, and extracts data.
        In a real scenario, this would likely be more complex (filtering seen URLs, etc).
        For now, it just aggregates everything.
        """
        all_news_data: List[RawNewsData] = []

        for source in self.sources:
            try:
                # 1. Check for news URLs
                new_urls = await source.check_for_news()
                if not new_urls:
                    continue

                # 2. Extract data (potentially filtered by Separator agent in between steps in future)
                # For now, we extract all found news
                news_items = await source.extract_data(new_urls)
                all_news_data.extend(news_items)

            except Exception as e:
                print(f"Error collecting from {source.source_link}: {e}")
                # We don't want to fail the whole batch if one source fails
                continue

        return all_news_data
