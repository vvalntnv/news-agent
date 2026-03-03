from typing import Self

from pydantic import BaseModel
from application.ai.workflow.step import ConditionFunction, WorkflowStep
from application.ai.workflow.workflow import Workflow
from domain.ai.protocols import Agent


class WorkflowBuilder:
    def __init__(self) -> None:
        self._has_added_start_step = False
        self._initial_step: WorkflowStep

    @classmethod
    def initialize(cls, starting_step: WorkflowStep | None = None) -> Self:
        builder = cls()

        if starting_step is not None:
            builder.add_starting_step(starting_step)

        return builder

    def build(self) -> Workflow:
        if self.is_workflow_empty:
            # ReviewComment: here we need custom exception
            raise Exception("You have to first define the entry step")

        if not self.has_agent:
            raise Exception(
                "The workflow builder does not have an agent to place in workflow!"
            )

        return Workflow(self._initial_step, self.agent)

    def add_agent(self, agent: Agent) -> Self:
        self.agent = agent

        return self

    def add_starting_step(self, initial_step: WorkflowStep) -> Self:
        if not self.is_workflow_empty:
            # ReviewComment: here we need custom exception
            raise Exception("There is currently an assigned first step")

        self._initial_step = initial_step
        return self

    def add_step(
        self,
        start: WorkflowStep,
        end: WorkflowStep,
    ) -> Self:
        if self.is_workflow_empty:
            self.add_starting_step(start)

        start.add_direct_transition(end)

        return self

    def add_transition[S: BaseModel, O: BaseModel](
        self,
        premise: WorkflowStep,
        condition_func: ConditionFunction[S],
        consiquence: WorkflowStep[S, O],
    ) -> Self:
        if self.is_workflow_empty:
            self.add_starting_step(premise)

        premise.add_transition(condition_func, consiquence)
        return self

    @property
    def is_workflow_empty(self) -> bool:
        return not hasattr(self, "_initial_step")

    @property
    def has_agent(self) -> bool:
        return hasattr(self, "agent")
