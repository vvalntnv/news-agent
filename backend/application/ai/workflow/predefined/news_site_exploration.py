import random

from pydantic import BaseModel, Field

from application.ai.workflow.builder import WorkflowBuilder
from application.ai.workflow.step import WorkflowStep
from application.ai.workflow.workflow import Workflow
from domain.ai.protocols import Agent
from domain.news.value_objects import ScrapeInformation
from infrastructure.sources.web_scraper_source import WebScraperSource


class NewsSiteExplorationInput(BaseModel):
    scraping_url: str = Field(min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=5)
    sample_articles_count: int = Field(default=2, ge=1, le=5)
    extra_guidance: str | None = None
    example_articles: list[str] = Field(default_factory=list)


class NewsSiteExplorationDependencies(BaseModel):
    scraping_url: str


class NewsSiteExplorationState(BaseModel):
    scraping_url: str
    max_attempts: int
    attempts_made: int = 0
    sample_articles_count: int
    sample_article_urls: list[str] = Field(default_factory=list)
    latest_result: ScrapeInformation | None = None


def _build_feed_exploration_prompt(
    input_data: NewsSiteExplorationInput,
    attempt_number: int,
) -> str:
    lines: list[str] = [
        "Explore the news website and extract feed-level CSS selectors for scraping.",
        f"Target URL: {input_data.scraping_url}",
        f"Attempt number: {attempt_number}",
        "Return only a valid ScrapeInformation object.",
        "Selectors must be specific and stable.",
        "Use only valid CSS selectors (e.g., `.article-card`, `#main > article`, `article h2`) and keep them deterministic.",
        "For this step, prioritize articleContainers, titlesContainers, timestampsConteiners, and summaryContainers.",
        "Do not touch `mainArticleContainer` yet; main_article_container should remain unset until we explore individual articles.",
        "When media is unavailable, use null for imageContainers/videoContainers/audioContainers.",
        "Use timestampsConteiners exactly as defined in the schema.",
    ]

    if input_data.extra_guidance is not None:
        lines.append(f"Additional guidance: {input_data.extra_guidance}")

    return "\n".join(lines)


def _build_article_exploration_prompt(
    *,
    input_data: NewsSiteExplorationInput,
    attempt_number: int,
    partial_result: ScrapeInformation,
    sample_article_urls: list[str],
) -> str:
    lines: list[str] = [
        "Use the sampled article URLs to complete the missing scraping selectors.",
        f"Target URL: {input_data.scraping_url}",
        f"Attempt number: {attempt_number}",
        "Use the browse tool to inspect each sampled article URL with sanitize=true.",
        "Prefer root_of_analysis='article' and retry with root_of_analysis='body' when needed.",
        "Return only a valid ScrapeInformation object.",
        "All selectors you provide must be valid CSS selectors (e.g., `.story h1`, `#article .meta`) and deterministic.",
        "Be as precise as possible and include as many relevant selectors as needed for author, timestamp, and summary fields, even if they share the same container; document each identifier explicitly.",
        "While the page might show multiple authors/timestamps, pinpoint the single author and timestamp belonging to the article content—not global site attribution or unrelated widgets.",
        "This exploration targets single articles, so now populate `mainArticleContainer`—it must only be set when inspecting one article URL.",
        "All required fields must be present and non-empty where applicable.",
        "Keep already correct selectors and improve only what is missing or unstable.",
        "Current ScrapeInformation draft:",
        partial_result.model_dump_json(by_alias=True),
        "Sample article URLs:",
        "\n".join(sample_article_urls),
    ]

    if input_data.extra_guidance is not None:
        lines.append(f"Additional guidance: {input_data.extra_guidance}")

    return "\n".join(lines)


def _is_valid_scrape_information(result: ScrapeInformation) -> bool:
    has_article_selectors = len(result.article_containers) > 0
    has_title_selectors = len(result.titles_containers) > 0
    has_timestamp_selectors = len(result.timestamps_conteiners) > 0
    has_summary_selectors = len(result.summary_containers) > 0
    has_main_container = len(result.main_article_container.strip()) > 0
    has_author_container = len(result.author_container.strip()) > 0

    return (
        has_article_selectors
        and has_title_selectors
        and has_timestamp_selectors
        and has_summary_selectors
        and has_main_container
        and has_author_container
    )


def _should_retry_exploration(state: NewsSiteExplorationState) -> bool:
    has_remaining_attempts = state.attempts_made < state.max_attempts

    current_result = state.latest_result
    if current_result is None:
        return has_remaining_attempts

    is_current_result_valid = _is_valid_scrape_information(current_result)
    is_current_result_invalid = not is_current_result_valid

    return is_current_result_invalid and has_remaining_attempts


class ExploreNewsSiteStep(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    def __init__(
        self,
        *,
        state: NewsSiteExplorationState,
        input_data: NewsSiteExplorationInput,
    ) -> None:
        super().__init__(state=state)
        self.input_data = input_data

    async def execute_logic(self) -> ScrapeInformation:
        attempt_number = self.state.attempts_made + 1
        prompt = _build_feed_exploration_prompt(self.input_data, attempt_number)
        exploration_result = await self._run_exploration_with_agent(prompt)

        self.state.latest_result = exploration_result
        self.state.sample_article_urls = []
        self.state.attempts_made = attempt_number
        return exploration_result

    async def _run_exploration_with_agent(self, prompt: str) -> ScrapeInformation:
        run_result = await self.agent.run(prompt)
        if not isinstance(run_result, ScrapeInformation):
            raise TypeError("Expected ScrapeInformation result from workflow agent")

        return run_result


class ExtractSampleArticles(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    async def execute_logic(self) -> ScrapeInformation:
        latest_result = self.state.latest_result
        if latest_result is None:
            raise ValueError("Cannot extract sample articles without selectors")

        source = WebScraperSource(
            base_url=self.state.scraping_url,
            registered_scrapers=[latest_result],
        )
        try:
            all_articles = await source.check_for_news()
        finally:
            await source.close()

        article_urls = [article.url for article in all_articles]
        if len(article_urls) == 0:
            raise ValueError("No articles discovered with the provided selectors")

        max_sample_size = min(len(article_urls), self.state.sample_articles_count)
        self.state.sample_article_urls = random.sample(article_urls, k=max_sample_size)
        return latest_result


class ExploreArticles(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    def __init__(
        self,
        *,
        state: NewsSiteExplorationState,
        input_data: NewsSiteExplorationInput,
    ) -> None:
        super().__init__(state=state)
        self.input_data = input_data

    async def execute_logic(self) -> ScrapeInformation:
        partial_result = self.state.latest_result
        if partial_result is None:
            raise ValueError("Cannot explore articles without selectors")

        sample_article_urls = self.state.sample_article_urls
        if len(sample_article_urls) == 0:
            raise ValueError("Cannot explore articles without sampled article URLs")

        prompt = _build_article_exploration_prompt(
            input_data=self.input_data,
            attempt_number=self.state.attempts_made,
            partial_result=partial_result,
            sample_article_urls=sample_article_urls,
        )
        exploration_result = await self._run_exploration_with_agent(prompt)
        self.state.latest_result = exploration_result
        return exploration_result

    async def _run_exploration_with_agent(self, prompt: str) -> ScrapeInformation:
        run_result = await self.agent.run(prompt)
        if not isinstance(run_result, ScrapeInformation):
            raise TypeError("Expected ScrapeInformation result from workflow agent")

        return run_result


class ValidateNewsSiteSelectorsStep(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    async def execute_logic(self) -> ScrapeInformation:
        if self.state.latest_result is None:
            raise ValueError("Workflow validation step requires an exploration result")

        return self.state.latest_result


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
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
        sample_articles_count=input_data.sample_articles_count,
    )
    exploration_step = ExploreNewsSiteStep(state=state, input_data=input_data)
    sample_articles_step = ExtractSampleArticles(state=state)
    explore_articles_step = ExploreArticles(state=state, input_data=input_data)
    validation_step = ValidateNewsSiteSelectorsStep(state=state)

    return (
        WorkflowBuilder[
            NewsSiteExplorationState,
            ScrapeInformation,
            NewsSiteExplorationDependencies,
        ]
        .initialize(exploration_step)
        .add_default_agent(agent)
        .add_step(exploration_step, sample_articles_step)
        .add_step(sample_articles_step, explore_articles_step)
        .add_step(explore_articles_step, validation_step)
        .add_transition(validation_step, _should_retry_exploration, exploration_step)
        .build()
    )
