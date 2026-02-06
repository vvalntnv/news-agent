import pytest
from unittest.mock import AsyncMock, MagicMock

from domain.news.value_objects import ScrapeInformation
from infrastructure.sources.web_scraper_source import WebScraperSource

pytestmark = pytest.mark.anyio


async def test_web_scraper_skips_items_with_missing_title():
    html = """
    <html>
    <body>
        <div class="article">
            <a href="/valid"><span class="title">Valid Title</span></a>
        </div>
        <div class="article">
            <a href="/missing"><span class="not-title">No title</span></a>
        </div>
    </body>
    </html>
    """

    scraper_info = ScrapeInformation(
        scrapingUrl="https://example.com/",
        articleContainers=[".article"],
        titlesContainers=[".title"],
        timestampsConteiners=[".timestamp"],
        summaryContainers=[".summary"],
        mainArticleContainer=".article-content",
        authorContainer=".author",
    )

    source = WebScraperSource(
        base_url="https://example.com/",
        registered_scrapers=[scraper_info],
    )

    mock_response = MagicMock()
    mock_response.content = html.encode("utf-8")
    source.client.get = AsyncMock(return_value=mock_response)

    items = await source.check_for_news()

    assert len(items) == 1
    assert items[0].title == "Valid Title"
    assert items[0].url == "https://example.com/valid"
