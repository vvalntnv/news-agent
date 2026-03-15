import pytest
from bs4 import BeautifulSoup

from core.config import config
from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.validators import (
    validate_scrape_information,
)
from domain.news.value_objects import ScrapeInformation

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def configure_selector_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 80)

    async def _fake_feed_selector_discovery(_result: ScrapeInformation) -> None:
        return None

    monkeypatch.setattr(
        "application.ai.workflow.predefined.news_site_exploration.validators.validate_feed_selector_discovery",
        _fake_feed_selector_discovery,
    )


def _build_state() -> NewsSiteExplorationState:
    input_data = NewsSiteExplorationInput(scraping_url="https://news.example")
    return NewsSiteExplorationState(
        input_data=input_data,
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
        sample_articles_count=input_data.sample_articles_count,
        sample_article_urls=["https://news.example/a", "https://news.example/b"],
    )


def _build_result(main_selector: str) -> ScrapeInformation:
    return ScrapeInformation(
        scrapingUrl="https://news.example",
        articleContainers=["article"],
        titlesContainers=["h2"],
        timestampsConteiners=["time"],
        summaryContainers=["p.summary"],
        imageContainers=None,
        videoContainers=None,
        audioContainers=None,
        mainArticleContainer=main_selector,
        authorContainer=".article-author",
    )


async def test_validator_rejects_main_selector_without_strict_single_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_fetch_article_soup(
        *, client: object, article_url: str
    ) -> BeautifulSoup:
        _ = client
        _ = article_url
        return BeautifulSoup(
            """
            <html><body>
              <div>one</div>
              <div>two</div>
            </body></html>
            """,
            "html.parser",
        )

    monkeypatch.setattr(
        "application.ai.workflow.predefined.news_site_exploration.validators._fetch_article_soup",
        _fake_fetch_article_soup,
    )

    with pytest.raises(ValueError, match="must match exactly one element"):
        await validate_scrape_information(_build_state(), _build_result("div"))


async def test_validator_rejects_link_heavy_main_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_fetch_article_soup(
        *, client: object, article_url: str
    ) -> BeautifulSoup:
        _ = client
        _ = article_url
        return BeautifulSoup(
            """
            <html><body>
              <article class='main-content'>
                <p><a href='/x'>Link one text that is very long and dominates content</a></p>
                <p><a href='/y'>Link two text that is very long and dominates content</a></p>
              </article>
            </body></html>
            """,
            "html.parser",
        )

    monkeypatch.setattr(
        "application.ai.workflow.predefined.news_site_exploration.validators._fetch_article_soup",
        _fake_fetch_article_soup,
    )

    with pytest.raises(ValueError, match="too link-heavy"):
        await validate_scrape_information(
            _build_state(),
            _build_result("article.main-content"),
        )
