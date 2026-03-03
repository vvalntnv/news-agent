from abc import ABC, abstractmethod
from typing import Callable

from pydantic import BaseModel

from domain.ai.protocols import Agent

type ConditionFunction[S: BaseModel] = Callable[[S], bool]


class WorkflowStep[S: BaseModel, O: BaseModel](ABC):
    state: S
    has_executed: bool
    result: O

    def __init__(self, state: S) -> None:
        self.transitions: list[tuple[ConditionFunction[S], WorkflowStep]] = []
        self.direct_step: WorkflowStep | None = None
        self.has_executed = False
        self.state = state
        self._agent: Agent

    def set_agent(self, agent: Agent) -> None:
        self.agent = agent

    def execute(self) -> O:
        if not self.has_agent_assigned:
            raise Exception("No agent is assigned to the current step")

        return self.execution_logic()

    @abstractmethod
    def execution_logic(self) -> O:
        pass

    @property
    def has_agent_assigned(self) -> bool:
        return hasattr(self, "agent")

    def add_direct_transition(self, next_step: "WorkflowStep") -> None:
        self.direct_step = next_step

    def add_transition(
        self,
        condition: ConditionFunction[S],
        next_step: "WorkflowStep",
    ) -> None:
        if self.direct_step is not None:
            raise Exception(
                "There is currently a direct next step being set. Adding "
                "transitions does not change the graph. Remove the direct_step "
                "or add condition to it, by using the `add_transition` method"
            )
        cause_consequence_pair = (condition, next_step)
        self.transitions.append(cause_consequence_pair)

    def get_next(self) -> "WorkflowStep | None":
        if self.direct_step is not None:
            return self.direct_step

        for determine_switch, step in self.transitions:
            should_switch = determine_switch(self.state)

            if should_switch:
                return step

        return None
