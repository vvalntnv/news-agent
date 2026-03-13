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


@pytest.mark.slow
async def test_running_analyze_workflow() -> None:
    agent_factory = PydanticAgentAIFactory()
    scraping_url = "https://bntnews.bg/"
    dependencies = NewsSiteExplorationDependencies(scraping_url=scraping_url)
    browse_tool, client = BrowseTool.build_with_client()
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
        tools=[browse_tool],
        retries=5,
    )

    agent = agent_factory.create_agent(config)
    agent.add_dependency(dependencies)

    input_data = NewsSiteExplorationInput(scraping_url=scraping_url)
    workflow = PredefinedWorkflowRegistry().create_news_site_exploration_workflow(
        input_data, agent=agent
    )

    async with client:
        result = await workflow.execute_workflow()

    assert isinstance(result, ScrapeInformation)

    feed = WebScraperSource("", [result])
    try:
        news = await feed.check_for_news()
    finally:
        await feed.close()

    assert news, "expected at least one news item to be discovered"

    scraper = HtmlExtractor(registered_scrapers=[result])
    try:
        article = await scraper.extract(news[0])
    finally:
        await scraper.client.aclose()

    assert article.title == news[0].title
    assert article.article_url == news[0].url
    assert article.content.raw_content.strip()
    assert isinstance(article.content.quotes, list)
    assert article.author.strip()
    assert article.timestamp
