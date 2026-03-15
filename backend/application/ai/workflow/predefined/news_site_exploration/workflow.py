from application.ai.workflow.builder import WorkflowBuilder
from application.ai.workflow.predefined.news_site_exploration.context import (
    build_dependencies,
    resolve_workflow_result,
)
from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.steps import (
    explore_articles_step,
    explore_news_site_step,
    extract_sample_articles_step,
)
from application.ai.workflow.predefined.news_site_exploration.validators import (
    validate_scrape_information,
)
from application.ai.workflow.workflow import Workflow
from domain.ai.protocols import Agent
from domain.news.value_objects import ScrapeInformation


def build_news_site_exploration_workflow(
    *,
    input_data: NewsSiteExplorationInput,
    agent: Agent[ScrapeInformation, NewsSiteExplorationDependencies],
) -> Workflow[
    NewsSiteExplorationState,
    ScrapeInformation,
    NewsSiteExplorationDependencies,
]:
    state = NewsSiteExplorationState(
        input_data=input_data,
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
        sample_articles_count=input_data.sample_articles_count,
    )

    builder = WorkflowBuilder[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]()

    workflow = (
        builder.register_function_step(
            state=state,
            function=explore_news_site_step,
        )
        .register_function_step(
            state=state,
            function=extract_sample_articles_step,
        )
        .register_function_step(
            state=state,
            function=explore_articles_step,
        )
        .set_workflow_name("news_site_exploration")
        .add_starting_step(explore_news_site_step)
        .add_default_agent(agent)
        .with_dependency_provider(build_dependencies)
        .with_result_resolver(resolve_workflow_result)
        .add_step(explore_news_site_step, extract_sample_articles_step)
        .add_step(extract_sample_articles_step, explore_articles_step)
        .add_validator(explore_articles_step, validate_scrape_information)
        .set_step_validation_retries(
            explore_articles_step,
            input_data.max_attempts - 1,
        )
        .build()
    )

    return workflow
