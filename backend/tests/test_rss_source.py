import pytest
from unittest.mock import MagicMock
from news_sourcing.models import RSSInformation
from news_sourcing.models.loader import NewsLoader
from news_sourcing.rss import RSSNewsSource
from feedparser import FeedParserDict

pytestmark = pytest.mark.anyio


async def test_rss_source_check_for_news(monkeypatch):
    # Mock feedparser.parse
    mock_feed = FeedParserDict()
    mock_feed.entries = [  # type: ignore
        FeedParserDict(title="Test Title 1", link="http://example.com/1"),
        FeedParserDict(title="Test Title 2", link="http://example.com/2"),
        FeedParserDict(link="http://example.com/3"),  # Missing title
    ]

    # We need to mock the executor call since check_for_news runs in an executor
    # But simpler is to mock feedparser.parse.
    # However, it runs in loop.run_in_executor(None, feedparser.parse, url)
    # So simply mocking feedparser.parse should work if it's imported in the module.

    mock_parse = MagicMock(return_value=mock_feed)
    monkeypatch.setattr("news_sourcing.rss.feedparser.parse", mock_parse)

    # Create RSSInformation
    rss_info = RSSInformation(rssFeed="http://example.com/feed")

    # Initialize RSSNewsSource
    source = RSSNewsSource(
        base_url="http://example.com", registered_rss_feeds=[rss_info]
    )

    # Run check_for_news
    news_items = await source.check_for_news()

    assert len(news_items) == 3
    assert news_items[0].title == "Test Title 1"
    assert news_items[0].link == "http://example.com/1"
    assert news_items[1].title == "Test Title 2"
    assert news_items[1].link == "http://example.com/2"
    assert news_items[2].title is None
    assert news_items[2].link == "http://example.com/3"


async def test_rss_source_deduplication(monkeypatch):
    # Mock feedparser.parse
    mock_feed = FeedParserDict()
    mock_feed.entries = [  # type: ignore
        FeedParserDict(title=None, link="http://example.com/1"),
        FeedParserDict(
            title="Test Title 1", link="http://example.com/1"
        ),  # Better version of same link
    ]

    mock_parse = MagicMock(return_value=mock_feed)
    monkeypatch.setattr("news_sourcing.rss.feedparser.parse", mock_parse)

    rss_info = RSSInformation(rssFeed="http://example.com/feed")
    source = RSSNewsSource(
        base_url="http://example.com", registered_rss_feeds=[rss_info]
    )

    news_items = await source.check_for_news()

    assert len(news_items) == 1
    assert news_items[0].title == "Test Title 1"
    assert news_items[0].link == "http://example.com/1"


async def test_bta_rss():
    loader = NewsLoader()
    _, rss_feeds = loader.load_scrapers_data()

    source = RSSNewsSource(
        base_url="http://example.com",
        registered_rss_feeds=rss_feeds,
    )

    news_data = await source.check_for_news()
    breakpoint()

    assert len(news_data) > 0
