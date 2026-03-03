from pydantic import BaseModel, Field

from application.ai.workflow.builder import WorkflowBuilder
from application.ai.workflow.step import WorkflowStep
from application.ai.workflow.workflow import Workflow
from domain.ai.configuration import AIConfiguration
from domain.ai.protocols import AIFactory
from domain.news.value_objects import ScrapeInformation
from infrastructure.ai.factory import PydanticAgentAIFactory


class NewsSiteExplorationInput(BaseModel):
    scraping_url: str = Field(min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=5)
    extra_guidance: str | None = None


class NewsSiteExplorationDependencies(BaseModel):
    scraping_url: str


class NewsSiteExplorationState(BaseModel):
    scraping_url: str
    max_attempts: int
    attempts_made: int = 0
    latest_result: ScrapeInformation | None = None


def _build_exploration_prompt(
    input_data: NewsSiteExplorationInput,
    attempt_number: int,
) -> str:
    lines: list[str] = [
        "Explore the news website and extract CSS selectors for scraping.",
        f"Target URL: {input_data.scraping_url}",
        f"Attempt number: {attempt_number}",
        "Return only a valid ScrapeInformation object.",
        "Selectors must be specific and stable.",
        "All required fields must be present.",
        "When media is unavailable, use null for imageContainers/videoContainers/audioContainers.",
        "Use timestampsConteiners exactly as defined in the schema.",
    ]

    if input_data.extra_guidance is not None:
        lines.append(f"Additional guidance: {input_data.extra_guidance}")

    return "\n".join(lines)


def _build_agent_configuration(
    input_data: NewsSiteExplorationInput,
) -> AIConfiguration[ScrapeInformation, NewsSiteExplorationDependencies]:
    dependencies = NewsSiteExplorationDependencies(scraping_url=input_data.scraping_url)

    return AIConfiguration[ScrapeInformation, NewsSiteExplorationDependencies](
        model_name="openai/gpt-5.1-mini",
        output_type=ScrapeInformation,
        deps=dependencies,
        retries=2,
        output_retries=2,
        instructions=(
            "You are an expert website structure analyst. "
            "Find article, title, timestamp, summary, media, and author selectors."
        ),
        system_prompt=[
            "Return schema-valid extraction output only.",
            "Prefer CSS selectors that generalize across article cards.",
            "Do not invent selectors that are not visible in the page structure.",
        ],
    )


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
        prompt = _build_exploration_prompt(self.input_data, attempt_number)
        exploration_result = await self._run_exploration_with_agent(prompt)

        self.state.latest_result = exploration_result
        self.state.attempts_made = attempt_number
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
    input_data: NewsSiteExplorationInput,
    *,
    ai_factory: AIFactory | None = None,
) -> Workflow[
    NewsSiteExplorationState,
    ScrapeInformation,
    NewsSiteExplorationDependencies,
]:
    resolved_factory = ai_factory or PydanticAgentAIFactory()
    configuration = _build_agent_configuration(input_data)
    agent = resolved_factory.create_agent(configuration)

    dependencies = NewsSiteExplorationDependencies(scraping_url=input_data.scraping_url)
    configured_agent = agent.add_dependency(dependencies)

    state = NewsSiteExplorationState(
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
    )
    exploration_step = ExploreNewsSiteStep(state=state, input_data=input_data)
    validation_step = ValidateNewsSiteSelectorsStep(state=state)

    return (
        WorkflowBuilder[
            NewsSiteExplorationState,
            ScrapeInformation,
            NewsSiteExplorationDependencies,
        ]
        .initialize(exploration_step)
        .add_agent(configured_agent)
        .add_step(exploration_step, validation_step)
        .add_transition(validation_step, _should_retry_exploration, exploration_step)
        .build()
    )
