from collections.abc import AsyncIterable, Callable
from typing import cast

import pytest
from bs4 import BeautifulSoup

from application.ai.workflow.predefined.news_site_exploration import (
    validators as news_site_exploration_validators,
)
from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
    build_news_site_exploration_workflow,
)
from application.ai.workflow.predefined.news_site_exploration.steps import (
    extract_sample_articles_step as extract_sample_articles_step_module,
)
from application.ai.workflow.predefined.news_site_exploration.steps.extract_sample_articles_step import (
    ExtractSampleArticlesStep,
)
from core.config import config
from core.errors import WorkflowStepRetryExhaustedError
from domain.ai.protocols import Agent
from domain.news.entities import NewsItem
from domain.news.value_objects import ScrapeInformation

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def stub_article_soup_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 80)

    async def _fake_fetch_article_soup(
        *, client: object, article_url: str
    ) -> BeautifulSoup:
        _ = client
        _ = article_url
        html = """
        <html>
          <body>
            <article class='main-content'>
              <h1>Title</h1>
              <p>Paragraph one with enough content for extraction validation and stable article extraction behavior across pages.</p>
              <p>Paragraph two with additional details from the article body and multiple sentences to ensure text length is high enough for strict semantic checks.</p>
              <div class='article-author'>Author Name</div>
            </article>
          </body>
        </html>
        """
        return BeautifulSoup(html, "html.parser")

    monkeypatch.setattr(
        news_site_exploration_validators,
        "_fetch_article_soup",
        _fake_fetch_article_soup,
    )

    async def _fake_feed_selector_discovery(_result: ScrapeInformation) -> None:
        return None

    monkeypatch.setattr(
        news_site_exploration_validators,
        "validate_feed_selector_discovery",
        _fake_feed_selector_discovery,
    )

    async def _fake_select_structured_article_urls(
        self: ExtractSampleArticlesStep,
        *,
        article_urls: list[str],
        sample_size: int,
    ) -> list[str]:
        _ = self
        return article_urls[:sample_size]

    monkeypatch.setattr(
        ExtractSampleArticlesStep,
        "_select_structured_article_urls",
        _fake_select_structured_article_urls,
    )


def _build_partial_scrape_information(scraping_url: str) -> ScrapeInformation:
    return ScrapeInformation(
        scrapingUrl=scraping_url,
        articleContainers=["article"],
        titlesContainers=["h2"],
        timestampsConteiners=["time"],
        summaryContainers=["p.summary"],
        imageContainers=None,
        videoContainers=None,
        audioContainers=None,
        mainArticleContainer="",
        authorContainer="",
    )


def _build_complete_scrape_information(scraping_url: str) -> ScrapeInformation:
    return ScrapeInformation(
        scrapingUrl=scraping_url,
        articleContainers=["article"],
        titlesContainers=["h2"],
        timestampsConteiners=["time"],
        summaryContainers=["p.summary"],
        imageContainers=["figure img"],
        videoContainers=None,
        audioContainers=None,
        mainArticleContainer="article.main-content",
        authorContainer=".article-author",
    )


class _StubAgent:
    output_type = ScrapeInformation
    dependencies_type = NewsSiteExplorationDependencies
    history_tracker: Callable[[list[object]], list[object]] = staticmethod(
        lambda messages: messages
    )
    tools: list[object] = []

    def __init__(self, responses: list[ScrapeInformation]) -> None:
        self._responses = responses
        self.prompts: list[str] = []
        self.dependencies: list[NewsSiteExplorationDependencies] = []

    def add_dependency(
        self, dependency: NewsSiteExplorationDependencies
    ) -> "_StubAgent":
        self.dependencies.append(dependency)
        return self

    async def run(self, prompt: str) -> ScrapeInformation:
        self.prompts.append(prompt)
        if len(self._responses) == 0:
            raise AssertionError("No more responses configured for stub agent")

        return self._responses.pop(0)

    async def stream(self, prompt: str) -> AsyncIterable[str]:
        if False:
            yield prompt


class _FakeWebScraperSource:
    def __init__(
        self,
        base_url: str,
        registered_scrapers: list[ScrapeInformation],
        discovered_articles: list[NewsItem],
    ) -> None:
        self.base_url = base_url
        self.registered_scrapers = registered_scrapers
        self.discovered_articles = discovered_articles

    async def check_for_news(self) -> list[NewsItem]:
        return self.discovered_articles

    async def close(self) -> None:
        return None


def _build_fake_web_scraper_source_factory(
    discovered_articles: list[NewsItem],
) -> Callable[..., _FakeWebScraperSource]:
    def _build_fake_web_scraper_source(
        *,
        base_url: str,
        registered_scrapers: list[ScrapeInformation],
    ) -> _FakeWebScraperSource:
        return _FakeWebScraperSource(
            base_url=base_url,
            registered_scrapers=registered_scrapers,
            discovered_articles=discovered_articles,
        )

    return _build_fake_web_scraper_source


async def test_workflow_extracts_sample_articles_and_completes_scrape_information(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraping_url = "https://news.example"
    partial_result = _build_partial_scrape_information(scraping_url)
    complete_result = _build_complete_scrape_information(scraping_url)

    discovered_articles = [
        NewsItem(title="One", url="https://news.example/a"),
        NewsItem(title="Two", url="https://news.example/b"),
        NewsItem(title="Three", url="https://news.example/c"),
    ]
    monkeypatch.setattr(
        extract_sample_articles_step_module,
        "WebScraperSource",
        _build_fake_web_scraper_source_factory(discovered_articles),
    )

    stub_agent = _StubAgent([partial_result, complete_result])
    workflow = build_news_site_exploration_workflow(
        input_data=NewsSiteExplorationInput(
            scraping_url=scraping_url,
            max_attempts=1,
            sample_articles_count=2,
        ),
        agent=cast(
            Agent[ScrapeInformation, NewsSiteExplorationDependencies],
            stub_agent,
        ),
    )

    result = await workflow.execute_workflow()

    assert result == complete_result
    workflow_state = cast(NewsSiteExplorationState, workflow.entrypoint.state)
    assert len(workflow_state.sample_article_urls) == 2
    assert workflow_state.article_refinement_attempts == 1
    assert len(stub_agent.prompts) == 2
    assert len(stub_agent.dependencies) == 3
    for dependency in stub_agent.dependencies:
        assert dependency.scraping_url == scraping_url


async def test_workflow_retries_when_completed_scrape_information_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraping_url = "https://news.example"
    first_partial = _build_partial_scrape_information(scraping_url)
    invalid_completed = _build_partial_scrape_information(scraping_url)
    valid_completed = _build_complete_scrape_information(scraping_url)

    discovered_articles = [
        NewsItem(title="One", url="https://news.example/a"),
        NewsItem(title="Two", url="https://news.example/b"),
    ]
    monkeypatch.setattr(
        extract_sample_articles_step_module,
        "WebScraperSource",
        _build_fake_web_scraper_source_factory(discovered_articles),
    )

    stub_agent = _StubAgent(
        [
            first_partial,
            invalid_completed,
            valid_completed,
        ]
    )
    workflow = build_news_site_exploration_workflow(
        input_data=NewsSiteExplorationInput(
            scraping_url=scraping_url,
            max_attempts=2,
            sample_articles_count=2,
        ),
        agent=cast(
            Agent[ScrapeInformation, NewsSiteExplorationDependencies],
            stub_agent,
        ),
    )

    result = await workflow.execute_workflow()

    assert result == valid_completed
    workflow_state = cast(NewsSiteExplorationState, workflow.entrypoint.state)
    assert workflow_state.article_refinement_attempts == 2
    assert len(stub_agent.prompts) == 3


async def test_workflow_fails_when_validation_retries_are_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraping_url = "https://news.example"
    partial_result = _build_partial_scrape_information(scraping_url)
    invalid_completed_first = _build_partial_scrape_information(scraping_url)
    invalid_completed_second = _build_partial_scrape_information(scraping_url)

    discovered_articles = [
        NewsItem(title="One", url="https://news.example/a"),
        NewsItem(title="Two", url="https://news.example/b"),
    ]
    monkeypatch.setattr(
        extract_sample_articles_step_module,
        "WebScraperSource",
        _build_fake_web_scraper_source_factory(discovered_articles),
    )

    stub_agent = _StubAgent(
        [
            partial_result,
            invalid_completed_first,
            invalid_completed_second,
        ]
    )
    workflow = build_news_site_exploration_workflow(
        input_data=NewsSiteExplorationInput(
            scraping_url=scraping_url,
            max_attempts=2,
            sample_articles_count=2,
        ),
        agent=cast(
            Agent[ScrapeInformation, NewsSiteExplorationDependencies],
            stub_agent,
        ),
    )

    with pytest.raises(WorkflowStepRetryExhaustedError):
        await workflow.execute_workflow()
