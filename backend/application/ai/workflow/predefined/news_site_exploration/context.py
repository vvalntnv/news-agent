from core.errors import WorkflowNoResultError

from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationState,
)
from domain.news.value_objects import ScrapeInformation


def resolve_workflow_result(state: NewsSiteExplorationState) -> ScrapeInformation:
    if state.latest_result is None:
        raise WorkflowNoResultError(workflow_name="news_site_exploration")

    return state.latest_result


def build_dependencies(
    state: NewsSiteExplorationState,
) -> NewsSiteExplorationDependencies:
    return NewsSiteExplorationDependencies(scraping_url=state.scraping_url)
