from typing import List
import feedparser
import asyncio

from news_sourcing.models import News, RSSInformation
from feedparser import FeedParserDict
from .protocols import NewsSource


class RSSNewsSource(NewsSource):
    """
    Abstract Base Class for RSS-based news sources.
    """

    def __init__(self, base_url: str, registered_rss_feeds: list[RSSInformation]):
        self.rss_informations: dict[str, RSSInformation] = {}
        self.source_link = base_url

        for rss in registered_rss_feeds:
            hostname = rss.get_host()
            self.rss_informations.update({hostname: rss})

    async def check_for_news(self) -> List[News]:
        """
        Fetches the RSS feeds and returns a list of entry links (or titles as IDs).
        """
        articles: dict[str, News] = {}

        for rss_info in self.rss_informations.values():
            news = await self._fetch_feed(rss_info)
            for article in news:
                if article.link not in articles:
                    articles.update({article.link: article})
                else:
                    loaded_article = articles[article.link]
                    does_already_have_article_title = loaded_article.title is None
                    does_current_article_have_title = article.title is not None

                    if (
                        does_already_have_article_title
                        and does_current_article_have_title
                    ):
                        articles.update({article.link: article})

        return list(articles.values())

    async def _fetch_feed(self, rss_info: RSSInformation) -> list[News]:
        # feedparser is synchronous, so we run it in an executor
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, rss_info.rss_feed)

        return self._transform_feed_to_news(feed)

    def _transform_feed_to_news(self, feed: FeedParserDict) -> list[News]:
        def _process_single_entry(entry: dict | FeedParserDict):
            link = entry.get("link")
            title = entry.get("title")

            if link is None:
                return None

            return News(title=title, link=link)

        news = []
        for entry in feed.entries:
            processed = _process_single_entry(entry)
            if processed:
                news.append(processed)
        return news
