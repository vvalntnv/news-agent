from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.prompts import (
    build_feed_exploration_prompt,
)
from application.ai.workflow.step import WorkflowStep
from domain.news.value_objects import ScrapeInformation


class ExploreNewsSiteStep(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    async def execute_logic(self) -> ScrapeInformation:
        attempt_number = 1
        prompt = build_feed_exploration_prompt(self.state.input_data, attempt_number)
        exploration_result = await self._run_exploration_with_agent(prompt=prompt)
        self.state.latest_result = exploration_result
        self.state.sample_article_urls = []
        return exploration_result

    async def _run_exploration_with_agent(self, *, prompt: str) -> ScrapeInformation:
        max_agent_attempts = 3
        last_error: Exception | None = None

        for local_attempt in range(1, max_agent_attempts + 1):
            strict_prompt = (
                f"{prompt}\n\n"
                "OUTPUT CONTRACT: Return only a valid ScrapeInformation JSON object. "
                "No prose. No markdown. No analysis text."
            )
            try:
                run_result = await self.agent.run(strict_prompt)
                if not isinstance(run_result, ScrapeInformation):
                    raise TypeError(
                        "Expected ScrapeInformation result from workflow agent"
                    )

                return run_result
            except Exception as error:
                last_error = error
                has_remaining_attempts = local_attempt < max_agent_attempts
                if has_remaining_attempts:
                    continue

                raise

        assert last_error is not None
        raise last_error
