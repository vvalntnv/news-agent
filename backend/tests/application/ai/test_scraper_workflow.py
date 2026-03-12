import pytest

from application.ai.tools.browse import BrowseTool
from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
)
from application.ai.workflow.registry import PredefinedWorkflowRegistry
from domain.ai.configuration import AIConfiguration
from domain.news.value_objects import ScrapeInformation
from infrastructure.ai.factory import PydanticAgentAIFactory
from infrastructure.extraction.html_extractor import HtmlExtractor
from infrastructure.sources.web_scraper_source import WebScraperSource

pytestmark = pytest.mark.anyio


async def test_running_analyze_workflow() -> None:
    agent_factory = PydanticAgentAIFactory()
    scraping_url = "https://bntnews.bg/"
    dependencies = NewsSiteExplorationDependencies(scraping_url=scraping_url)
    config = AIConfiguration[ScrapeInformation, NewsSiteExplorationDependencies](
        provider_name="groq",
        model_alias="primary",
        # model_name="openai/gpt-oss-120b",
        output_type=ScrapeInformation,
        agent_name="news-site-explorer",
        instructions=[
            "You are a site analyst that inspects a news homepage and nearby sections.",
            "Identify stable CSS selectors for articles, titles, timestamps, summaries, media blocks, "
            "and author information so downstream scrapers can reliably extract the data.",
            "Return a valid ScrapeInformation object without extra narrative and prefer selectors that survive layout tweaks.",
        ],
        system_prompt=[
            "You will be presented with a feed of news. What you need to do is pick 1 or 2 random articles and analyze its contents in order to fill in the ScrapeInformation.",
            "Return only the fields declared in ScrapeInformation and explain analysis in concise bullet form if needed.",
        ],
        deps=dependencies,
        tools=[BrowseTool()],
        retries=5,
    )

    agent = agent_factory.create_agent(config)
    agent.add_dependency(dependencies)

    input_data = NewsSiteExplorationInput(scraping_url=scraping_url)
    workflow = PredefinedWorkflowRegistry().create_news_site_exploration_workflow(
        input_data, agent=agent
    )

    result = await workflow.execute_workflow()  # noqa: F841

    assert isinstance(result, ScrapeInformation)

    feed = WebScraperSource("", [result])
    news = await feed.check_for_news()
    scraper = HtmlExtractor(registered_scrapers=[result])

    article = await scraper.extract(news[0])
    breakpoint()
