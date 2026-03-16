import pytest

from application.ai.workflow.predefined.news_site_exploration.context import (
    resolve_workflow_result,
)
from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
)
from core.errors import WorkflowNoResultError
from domain.news.value_objects import ScrapeInformation


def _build_state() -> NewsSiteExplorationState:
    input_data = NewsSiteExplorationInput(scraping_url="https://news.example")
    return NewsSiteExplorationState(
        input_data=input_data,
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
        sample_articles_count=input_data.sample_articles_count,
    )


def _build_result() -> ScrapeInformation:
    return ScrapeInformation(
        scrapingUrl="https://news.example",
        articleContainers=["article"],
        titlesContainers=["h2"],
        timestampsConteiners=["time"],
        summaryContainers=["p.summary"],
        imageContainers=None,
        videoContainers=None,
        audioContainers=None,
        mainArticleContainer="article.main-content",
        authorContainer=".author",
    )


def test_resolve_workflow_result_raises_when_no_result_in_state() -> None:
    with pytest.raises(WorkflowNoResultError):
        resolve_workflow_result(_build_state())


def test_resolve_workflow_result_returns_latest_result() -> None:
    state = _build_state()
    state.latest_result = _build_result()

    resolved_result = resolve_workflow_result(state)

    assert resolved_result == state.latest_result
