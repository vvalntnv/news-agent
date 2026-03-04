from dataclasses import dataclass
from enum import Enum
from typing import Callable

from pydantic import BaseModel

from application.ai.workflow.predefined.news_site_exploration import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
    build_news_site_exploration_workflow,
)
from application.ai.workflow.workflow import Workflow
from domain.ai.protocols import Agent
from domain.news.value_objects import ScrapeInformation


class PredefinedWorkflowName(str, Enum):
    NEWS_SITE_EXPLORATION = "news_site_exploration"


@dataclass(frozen=True)
class WorkflowDefinition[I: BaseModel, S: BaseModel, O: (BaseModel, str), D]:
    name: PredefinedWorkflowName
    description: str
    input_type: type[I]
    output_type: type[O]
    factory: Callable[[I, Agent[O, D]], Workflow[S, O, D]]


class PredefinedWorkflowRegistry:
    def __init__(self) -> None:
        self._news_site_exploration_definition = WorkflowDefinition(
            name=PredefinedWorkflowName.NEWS_SITE_EXPLORATION,
            description=(
                "Explores a news website and produces domain ScrapeInformation "
                "including media selectors"
            ),
            input_type=NewsSiteExplorationInput,
            output_type=ScrapeInformation,
            factory=self._build_news_site_exploration,
        )

    def list_workflows(self) -> tuple[PredefinedWorkflowName, ...]:
        return (PredefinedWorkflowName.NEWS_SITE_EXPLORATION,)

    def create_news_site_exploration_workflow(
        self,
        input_data: NewsSiteExplorationInput,
        agent: Agent[ScrapeInformation, NewsSiteExplorationDependencies],
    ) -> Workflow[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]:
        return self._news_site_exploration_definition.factory(input_data, agent)

    def get(
        self,
        workflow_name: PredefinedWorkflowName,
    ) -> WorkflowDefinition[
        NewsSiteExplorationInput,
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]:
        if workflow_name is PredefinedWorkflowName.NEWS_SITE_EXPLORATION:
            return self._news_site_exploration_definition

        raise ValueError(f"Workflow '{workflow_name.value}' is not registered")

    def _build_news_site_exploration(
        self,
        input_data: NewsSiteExplorationInput,
        agent: Agent[ScrapeInformation, NewsSiteExplorationDependencies],
    ) -> Workflow[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]:
        return build_news_site_exploration_workflow(
            input_data=input_data,
            agent=agent,
        )
