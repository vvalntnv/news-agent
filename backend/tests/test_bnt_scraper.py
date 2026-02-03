import json
import pytest
from pathlib import Path
from news_sourcing.models.models import ScrapeInformation
from news_sourcing.scraper_source import ScraperNewsSource


@pytest.mark.asyncio
async def test_bnt_scraper():
    # Load the BNT configuration
    bnt_config_path = Path("backend/sites/bnt.json")
    if not bnt_config_path.exists():
        bnt_config_path = Path("sites/bnt.json")

    # Handle running from root or backend dir
    if not bnt_config_path.exists():
        pytest.fail(f"Could not find bnt.json at {bnt_config_path.absolute()}")

    with open(bnt_config_path, "r") as f:
        config_data = json.load(f)

    # Create ScrapeInformation object
    # We need to map camelCase from JSON to snake_case for the model if not handled by alias
    # The ScrapeInformation model uses aliases (e.g. alias="scrapingUrl"), so direct unpacking should work if pydantic handles it.
    # Let's check how pydantic checks aliases. usually by_alias=True is for dumping.
    # For initializing, we can usually pass the aliased names if we set populate_by_name=True or similar,
    # or just pass the dict if it matches aliases.

    try:
        scraper_info = ScrapeInformation(**config_data)
    except Exception as e:
        pytest.fail(f"Failed to create ScrapeInformation: {e}")

    # Initialize ScraperNewsSource
    # base_url could be the scrapingUrl from the config
    base_url = scraper_info.scraping_url

    source = ScraperNewsSource(base_url=base_url, registered_scrapers=[scraper_info])

    try:
        # Check for news
        news_items = await source.check_for_news()
        breakpoint()

        # Verify results
        assert news_items is not None
        assert len(news_items) > 0, "No news items found"

        for news in news_items:
            assert news.link, "News item missing link"
            # Title might be None if extraction fails, but ideally it shouldn't
            print(f"Found news: {news.title} - {news.link}")

    finally:
        await source.close()
