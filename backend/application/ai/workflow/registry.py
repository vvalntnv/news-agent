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
from application.ai.workflow.state import WorkflowState
from application.ai.workflow.workflow import Workflow
from domain.ai.protocols import Agent
from domain.news.value_objects import ScrapeInformation


class PredefinedWorkflowName(str, Enum):
    NEWS_SITE_EXPLORATION = "news_site_exploration"


@dataclass(frozen=True)
class WorkflowDefinition[I: BaseModel, S: WorkflowState, O: BaseModel | str, D]:
    name: PredefinedWorkflowName
    description: str
    input_type: type[I]
    output_type: type[O]
    factory: Callable[[I, Agent[O, D]], Workflow[S, O, D]]


class PredefinedWorkflowRegistry:
    def __init__(self) -> None:
        self._definitions: dict[
            PredefinedWorkflowName,
            WorkflowDefinition[
                NewsSiteExplorationInput,
                NewsSiteExplorationState,
                ScrapeInformation,
                NewsSiteExplorationDependencies,
            ],
        ] = {}

        self._register_definition(
            WorkflowDefinition[
                NewsSiteExplorationInput,
                NewsSiteExplorationState,
                ScrapeInformation,
                NewsSiteExplorationDependencies,
            ](
                name=PredefinedWorkflowName.NEWS_SITE_EXPLORATION,
                description=(
                    "Explores a news website and produces domain ScrapeInformation "
                    "including media selectors"
                ),
                input_type=NewsSiteExplorationInput,
                output_type=ScrapeInformation,
                factory=self._build_news_site_exploration,
            )
        )

    def _register_definition(
        self,
        definition: WorkflowDefinition[
            NewsSiteExplorationInput,
            NewsSiteExplorationState,
            ScrapeInformation,
            NewsSiteExplorationDependencies,
        ],
    ) -> None:
        is_already_registered = definition.name in self._definitions
        if is_already_registered:
            raise ValueError(
                f"Workflow '{definition.name.value}' is already registered"
            )

        self._definitions[definition.name] = definition

    def list_workflows(self) -> tuple[PredefinedWorkflowName, ...]:
        return tuple(self._definitions.keys())

    def create_news_site_exploration_workflow(
        self,
        input_data: NewsSiteExplorationInput,
        agent: Agent[ScrapeInformation, NewsSiteExplorationDependencies],
    ) -> Workflow[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]:
        definition = self.get(PredefinedWorkflowName.NEWS_SITE_EXPLORATION)
        return definition.factory(input_data, agent)

    def get(
        self,
        workflow_name: PredefinedWorkflowName,
    ) -> WorkflowDefinition[
        NewsSiteExplorationInput,
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]:
        definition = self._definitions.get(workflow_name)
        if definition is not None:
            return definition

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
