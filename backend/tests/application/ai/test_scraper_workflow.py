import pytest

from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
)
from application.ai.workflow.registry import PredefinedWorkflowRegistry
from domain.ai.configuration import AIConfiguration
from domain.news.value_objects import ScrapeInformation
from infrastructure.ai.factory import PydanticAgentAIFactory

pytestmark = pytest.mark.anyio


async def test_running_analyze_workflow() -> None:
    agent_factory = PydanticAgentAIFactory()
    scraping_url = "https://bntnews.bg/"
    dependencies = NewsSiteExplorationDependencies(scraping_url=scraping_url)
    config = AIConfiguration[ScrapeInformation, NewsSiteExplorationDependencies](
        provider_name="groq",
        # model_alias="primary",
        model_name="openai/gpt-oss-120b",
        output_type=ScrapeInformation,
        agent_name="news-site-explorer",
        instructions=[
            "You are a site analyst that inspects a news homepage and nearby sections.",
            "Identify stable CSS selectors for articles, titles, timestamps, summaries, media blocks, "
            "and author information so downstream scrapers can reliably extract the data.",
            "Return a valid ScrapeInformation object without extra narrative and prefer selectors that survive layout tweaks.",
        ],
        system_prompt=[
            "Return only the fields declared in ScrapeInformation and explain analysis in concise bullet form if needed."
        ],
        deps=dependencies,
    )

    agent = agent_factory.create_agent(config)
    agent.add_dependency(dependencies)

    breakpoint()

    input_data = NewsSiteExplorationInput(scraping_url=scraping_url)
    workflow = PredefinedWorkflowRegistry().create_news_site_exploration_workflow(
        input_data, agent=agent
    )

    result = await workflow.execute_workflow()
