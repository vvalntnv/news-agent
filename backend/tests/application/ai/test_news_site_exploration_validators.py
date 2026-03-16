import pytest
from bs4 import BeautifulSoup

from application.ai.workflow.predefined.news_site_exploration import (
    validators as validators_module,
)
from core.config import config
from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.validators import (
    validate_feed_selector_discovery,
    validate_selector_stability,
    validate_scrape_information,
)
from domain.news.entities import NewsItem
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


async def test_validator_rejects_when_sample_urls_are_missing() -> None:
    state = _build_state()
    state.sample_article_urls = []

    with pytest.raises(ValueError, match="No sample article URLs"):
        await validate_scrape_information(state, _build_result("article.main-content"))


async def test_validator_rejects_main_selector_with_too_little_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 200)

    async def _fake_fetch_article_soup(
        *, client: object, article_url: str
    ) -> BeautifulSoup:
        _ = client
        _ = article_url
        return BeautifulSoup(
            """
            <html><body>
              <article class='main-content'>
                <p>short</p>
                <p>short</p>
              </article>
            </body></html>
            """,
            "html.parser",
        )

    monkeypatch.setattr(
        "application.ai.workflow.predefined.news_site_exploration.validators._fetch_article_soup",
        _fake_fetch_article_soup,
    )

    with pytest.raises(ValueError, match="too little text content"):
        await validate_scrape_information(
            _build_state(),
            _build_result("article.main-content"),
        )


async def test_validator_rejects_main_selector_with_too_few_paragraphs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 20)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 3)

    async def _fake_fetch_article_soup(
        *, client: object, article_url: str
    ) -> BeautifulSoup:
        _ = client
        _ = article_url
        return BeautifulSoup(
            """
            <html><body>
              <article class='main-content'>
                <p>Paragraph one with enough length.</p>
                <p>Paragraph two with enough length.</p>
              </article>
            </body></html>
            """,
            "html.parser",
        )

    monkeypatch.setattr(
        "application.ai.workflow.predefined.news_site_exploration.validators._fetch_article_soup",
        _fake_fetch_article_soup,
    )

    with pytest.raises(ValueError, match="too few paragraph elements"):
        await validate_scrape_information(
            _build_state(),
            _build_result("article.main-content"),
        )


def test_selector_stability_rejects_deep_main_selector() -> None:
    deep_main_selector = "main > div > div > article > div > p"

    with pytest.raises(ValueError, match="too deep and brittle"):
        validate_selector_stability(_build_result(deep_main_selector))


def test_selector_stability_rejects_positional_author_selector() -> None:
    result = _build_result("article.main-content")
    result.author_container = ".author:nth-child(2)"

    with pytest.raises(ValueError, match="uses positional pseudo selectors"):
        validate_selector_stability(result)


async def test_feed_discovery_validation_raises_when_no_news_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeEmptyWebScraperSource:
        def __init__(
            self,
            base_url: str,
            registered_scrapers: list[ScrapeInformation],
        ) -> None:
            _ = base_url
            _ = registered_scrapers

        async def check_for_news(self) -> list[NewsItem]:
            return []

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        validators_module, "WebScraperSource", _FakeEmptyWebScraperSource
    )

    with pytest.raises(ValueError, match="no news links were discovered"):
        await validate_feed_selector_discovery(_build_result("article.main-content"))
