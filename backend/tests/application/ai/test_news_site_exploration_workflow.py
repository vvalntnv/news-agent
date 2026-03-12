from collections.abc import AsyncIterable, Callable
from typing import cast

import pytest

from application.ai.workflow.predefined import news_site_exploration
from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
    build_news_site_exploration_workflow,
)
from domain.ai.protocols import Agent
from domain.news.entities import NewsItem
from domain.news.value_objects import ScrapeInformation

pytestmark = pytest.mark.anyio


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
        mainArticleContainer="main article",
        authorContainer=".author",
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

    def add_dependency(
        self, dependency: NewsSiteExplorationDependencies
    ) -> "_StubAgent":
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
    discovered_articles: list[NewsItem] = []

    def __init__(
        self, base_url: str, registered_scrapers: list[ScrapeInformation]
    ) -> None:
        self.base_url = base_url
        self.registered_scrapers = registered_scrapers

    async def check_for_news(self) -> list[NewsItem]:
        return self.discovered_articles

    async def close(self) -> None:
        return None


async def test_workflow_extracts_sample_articles_and_completes_scrape_information(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraping_url = "https://news.example"
    partial_result = _build_partial_scrape_information(scraping_url)
    complete_result = _build_complete_scrape_information(scraping_url)

    _FakeWebScraperSource.discovered_articles = [
        NewsItem(title="One", url="https://news.example/a"),
        NewsItem(title="Two", url="https://news.example/b"),
        NewsItem(title="Three", url="https://news.example/c"),
    ]
    monkeypatch.setattr(
        news_site_exploration, "WebScraperSource", _FakeWebScraperSource
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
    assert workflow_state.attempts_made == 1
    assert len(stub_agent.prompts) == 2


async def test_workflow_retries_when_completed_scrape_information_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraping_url = "https://news.example"
    first_partial = _build_partial_scrape_information(scraping_url)
    second_partial = _build_partial_scrape_information(scraping_url)
    invalid_completed = _build_partial_scrape_information(scraping_url)
    valid_completed = _build_complete_scrape_information(scraping_url)

    _FakeWebScraperSource.discovered_articles = [
        NewsItem(title="One", url="https://news.example/a"),
        NewsItem(title="Two", url="https://news.example/b"),
    ]
    monkeypatch.setattr(
        news_site_exploration, "WebScraperSource", _FakeWebScraperSource
    )

    stub_agent = _StubAgent(
        [
            first_partial,
            invalid_completed,
            second_partial,
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
    assert workflow_state.attempts_made == 2
    assert len(stub_agent.prompts) == 4
