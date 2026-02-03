from typing import List
import feedparser
import asyncio

from news_sourcing.models import News
from feedparser import FeedParserDict
from .protocols import NewsSource


class RSSNewsSource(NewsSource):
    """
    Abstract Base Class for RSS-based news sources.
    """

    def __init__(self, feed_url: str):
        self.source_link = feed_url
        self.feed_url = feed_url

    async def check_for_news(self) -> List[News]:
        """
        Fetches the RSS feed and returns a list of entry links (or titles as IDs).
        """
        # feedparser is synchronous, so we run it in an executor
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, self.feed_url)

        return self._transform_feed_to_news(feed)

    def _transform_feed_to_news(self, feed: FeedParserDict) -> list[News]:
        def _process_single_entry(entry: dict | FeedParserDict):
            assert not isinstance(entry, FeedParserDict), "Invalid feed received"

            link = entry.get("link")
            title = entry.get("title")

            assert link is not None, "Link should never be none"
            assert title is not None, "Title should never be none"

            return News(title=title, link=link)

        return [_process_single_entry(entry) for entry in feed.entries]
