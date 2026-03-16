import pytest

from application.ai.tools.browse import BrowseTool
from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
)
from application.ai.workflow.registry import PredefinedWorkflowRegistry
from domain.ai.configuration import AIConfiguration, ModelSettings
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
        model_settings=ModelSettings(
            temperature=0.0,
            top_p=1.0,
            max_tokens=900,
            timeout_seconds=60.0,
            stop_sequences=[],
        ),
        instructions=[
            "You are a site analyst that inspects a news homepage and nearby sections.",
            "Identify stable CSS selectors for articles, titles, timestamps, summaries, media blocks, "
            "and author information so downstream scrapers can reliably extract the data.",
            "Return a valid ScrapeInformation object without extra narrative and prefer selectors that survive layout tweaks.",
            "Never use brittle selectors like deep generic chains (`main > div > div > ...`) or positional pseudo selectors (`:first-of-type`, `:nth-child`).",
            "mainArticleContainer and authorContainer must generalize across multiple article pages, not a single page instance.",
        ],
        system_prompt=[
            "Workflow context: phase 1 discovers feed selectors, phase 2 validates article selectors on sampled article URLs.",
            "When selecting mainArticleContainer, compare all sampled article pages and choose one stable selector that works across all of them.",
            "Reject selectors that fail on even one sampled article page.",
            "Return only the fields declared in ScrapeInformation.",
        ],
        deps=dependencies,
        tools=[browse_tool],
        retries=8,
    )

    agent = agent_factory.create_agent(config)
    agent.add_dependency(dependencies)

    input_data = NewsSiteExplorationInput(
        scraping_url=scraping_url,
        max_attempts=5,
        sample_articles_count=2,
    )
    workflow = PredefinedWorkflowRegistry().create_news_site_exploration_workflow(
        input_data, agent=agent
    )

    async with client:
        result = await workflow.execute_workflow()

    feed = WebScraperSource("", [result])
    try:
        news = await feed.check_for_news()
    finally:
        await feed.close()

    assert news, "expected at least one news item to be discovered"

    scraper = HtmlExtractor(registered_scrapers=[result])
    article = None
    extraction_error: Exception | None = None
    try:
        for candidate_news in news[:10]:
            try:
                article = await scraper.extract(candidate_news)
                break
            except Exception as error:
                extraction_error = error
    finally:
        await scraper.client.aclose()

    assert article is not None, (
        "expected at least one discovered article to be extractable, "
        f"last_error={extraction_error}"
    )

    assert article.title is not None
    assert article.title.strip()
    assert article.article_url is not None
    assert article.article_url.strip()
    assert article.content.raw_content.strip()
    assert isinstance(article.content.quotes, list)
    assert article.author.strip()
    assert article.timestamp
