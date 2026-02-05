import pytest
from unittest.mock import MagicMock
from domain.news.value_objects import RSSInformation
from infrastructure.sites.loader import NewsLoader
from infrastructure.sources.rss_source import RSSNewsSource
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

    # Mock the executor call in local file.
    # Note: verify where RSSNewsSource imports feedparser.
    mock_parse = MagicMock(return_value=mock_feed)
    monkeypatch.setattr(
        "infrastructure.sources.rss_source.feedparser.parse", mock_parse
    )

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
    assert news_items[0].url == "http://example.com/1"
    assert news_items[1].title == "Test Title 2"
    assert news_items[1].url == "http://example.com/2"
    assert news_items[2].title is None
    assert news_items[2].url == "http://example.com/3"


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
    monkeypatch.setattr(
        "infrastructure.sources.rss_source.feedparser.parse", mock_parse
    )

    rss_info = RSSInformation(rssFeed="http://example.com/feed")
    source = RSSNewsSource(
        base_url="http://example.com", registered_rss_feeds=[rss_info]
    )

    news_items = await source.check_for_news()

    assert len(news_items) == 1
    assert news_items[0].title == "Test Title 1"
    assert news_items[0].url == "http://example.com/1"


async def test_bta_rss():
    loader = NewsLoader()
    _, rss_feeds = loader.load_scrapers_data()

    source = RSSNewsSource(
        base_url="http://example.com",
        registered_rss_feeds=rss_feeds,
    )

    news_data = await source.check_for_news()

    assert len(news_data) > 0
