from abc import ABC, abstractmethod
from collections.abc import Callable
import inspect
from typing import Awaitable

from pydantic import BaseModel

from domain.ai.protocols import Agent

type ConditionFunction[S: BaseModel] = Callable[[S], bool]


class WorkflowStep[S: BaseModel, O: (BaseModel, str), D](ABC):
    state: S
    has_executed: bool
    result: O

    def __init__(self, state: S) -> None:
        self.transitions: list[tuple[ConditionFunction[S], WorkflowStep[S, O, D]]] = []
        self.direct_step: WorkflowStep[S, O, D] | None = None
        self.has_executed = False
        self.state = state
        self.agent: Agent[O, D]

    def set_agent(self, agent: Agent[O, D]) -> None:
        self.agent = agent

    async def execute(self) -> O:
        if not self.has_agent_assigned:
            raise Exception("No agent is assigned to the current step")

        result_coro = self.execute_logic()
        result = await result_coro if inspect.isawaitable(result_coro) else result_coro
        self.has_executed = True
        self.result = result
        return result

    @abstractmethod
    def execute_logic(self) -> O | Awaitable[O]:
        raise NotImplementedError

    @property
    def has_agent_assigned(self) -> bool:
        return hasattr(self, "agent")

    def add_direct_transition(self, next_step: "WorkflowStep[S, O, D]") -> None:
        self.direct_step = next_step

    def add_transition(
        self,
        condition: ConditionFunction[S],
        next_step: "WorkflowStep[S, O, D]",
    ) -> None:
        if self.direct_step is not None:
            raise Exception(
                "There is currently a direct next step being set. Adding "
                "transitions does not change the graph. Remove the direct_step "
                "or add condition to it, by using the `add_transition` method"
            )
        cause_consequence_pair = (condition, next_step)
        self.transitions.append(cause_consequence_pair)

    def get_next(self) -> "WorkflowStep[S, O, D] | None":
        if self.direct_step is not None:
            return self.direct_step

        for get_condition, step in self.transitions:
            should_switch = get_condition(self.state)

            if should_switch:
                return step

        return None
