from typing import Self

from pydantic import BaseModel

from application.ai.workflow.step import ConditionFunction, WorkflowStep
from application.ai.workflow.workflow import Workflow
from domain.ai.protocols import Agent


class WorkflowBuilder[S: BaseModel, O: (BaseModel, str), D]:
    def __init__(self) -> None:
        self._initial_step: WorkflowStep[S, O, D] | None = None
        self._agent: Agent[O, D] | None = None

    @classmethod
    def initialize(
        cls,
        starting_step: WorkflowStep[S, O, D] | None = None,
    ) -> Self:
        builder = cls()

        if starting_step is not None:
            builder.add_starting_step(starting_step)

        return builder

    def build(self) -> Workflow[S, O, D]:
        if self._initial_step is None:
            raise ValueError("You must define a workflow entry step")

        if self._agent is None:
            raise ValueError("You must assign an agent before building a workflow")

        return Workflow(step_graph_entry=self._initial_step, agent=self._agent)

    def add_agent(self, agent: Agent[O, D]) -> Self:
        self._agent = agent
        return self

    def add_starting_step(self, initial_step: WorkflowStep[S, O, D]) -> Self:
        if self._initial_step is not None:
            raise ValueError("The workflow already has a starting step")

        self._initial_step = initial_step
        return self

    def add_step(
        self, start: WorkflowStep[S, O, D], end: WorkflowStep[S, O, D]
    ) -> Self:
        start.add_direct_transition(end)
        return self

    def add_transition(
        self,
        premise: WorkflowStep[S, O, D],
        condition_func: ConditionFunction[S],
        consequence: WorkflowStep[S, O, D],
    ) -> Self:
        premise.add_transition(condition_func, consequence)
        return self
