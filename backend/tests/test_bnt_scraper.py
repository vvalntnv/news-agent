import json
import pytest
from pathlib import Path
from domain.news.value_objects import ScrapeInformation
from infrastructure.sources.web_scraper_source import WebScraperSource


@pytest.mark.asyncio
async def test_bnt_scraper():
    # Load the BNT configuration
    bnt_config_path = Path("backend/infrastructure/sites/nova.json")
    if not bnt_config_path.exists():
        bnt_config_path = Path("infrastructure/sites/nova.json")

    # Handle running from root or backend dir
    if not bnt_config_path.exists():
        # fallback if running from root and backend is explicitly part of path
        bnt_config_path = Path("backend/infrastructure/sites/nova.json")

    # Try one more relative path if running from tests folder
    if not bnt_config_path.exists():
        bnt_config_path = Path("../infrastructure/sites/nova.json")

    if not bnt_config_path.exists():
        pytest.fail(f"Could not find bnt.json at {bnt_config_path.absolute()}")

    with open(bnt_config_path, "r") as f:
        config_data = json.load(f)

    # Create ScrapeInformation object
    try:
        scraper_info = ScrapeInformation(**config_data)
    except Exception as e:
        pytest.fail(f"Failed to create ScrapeInformation: {e}")

    # Initialize WebScraperSource
    # base_url could be the scrapingUrl from the config
    base_url = scraper_info.scraping_url

    source = WebScraperSource(base_url=base_url, registered_scrapers=[scraper_info])

    try:
        # Check for news
        news_items = await source.check_for_news()

        # Verify results
        assert news_items is not None
        assert len(news_items) > 0, "No news items found"

        for news in news_items:
            assert news.url, "News item missing url"
            # Title might be None if extraction fails, but ideally it shouldn't
            print(f"Found news: {news.title} - {news.url}")

    finally:
        await source.close()
