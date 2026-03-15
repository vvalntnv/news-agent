from abc import ABC, abstractmethod
from collections.abc import Callable
import inspect
from typing import Awaitable

from pydantic import BaseModel

from core.config import config
from core.errors import (
    WorkflowStepRetryExhaustedError,
    WorkflowStepValidationFailedError,
)
from domain.ai.protocols import Agent

type ConditionFunction[S: BaseModel] = Callable[[S], bool]
type StepValidator[S: BaseModel, O: BaseModel | str] = Callable[
    [S, O], None | Awaitable[None]
]
type StepFunction[S: BaseModel, O: BaseModel | str, D] = Callable[
    [S, Agent[O, D]], O | Awaitable[O]
]


class WorkflowStep[S: BaseModel, O: BaseModel | str, D](ABC):
    name: str
    state: S
    has_executed: bool
    result: O

    def __init__(self, state: S, name: str | None = None) -> None:
        self.transitions: list[tuple[ConditionFunction[S], WorkflowStep[S, O, D]]] = []
        self.direct_step: WorkflowStep[S, O, D] | None = None
        self.validators: list[StepValidator[S, O]] = []
        self.validation_max_retries = config.workflow_step_default_validation_retries
        self.has_executed = False
        self.state = state
        self.name = name or self.__class__.__name__
        self.agent: Agent[O, D]

    def set_agent(self, agent: Agent[O, D]) -> None:
        self.agent = agent

    def add_validator(self, validator: StepValidator[S, O]) -> None:
        self.validators.append(validator)

    def set_validation_retries(self, max_retries: int) -> None:
        if max_retries < 0:
            raise ValueError("Validation retries cannot be negative")

        self.validation_max_retries = max_retries

    async def execute(self) -> O:
        if not self.has_agent_assigned:
            raise Exception("No agent is assigned to the current step")

        attempt_number = 1
        while True:
            result_coro = self.execute_logic()
            result = (
                await result_coro if inspect.isawaitable(result_coro) else result_coro
            )

            try:
                await self._run_validators(result=result, attempt_number=attempt_number)
            except WorkflowStepValidationFailedError as validation_error:
                has_validation_error_slot = hasattr(self.state, "last_validation_error")
                if has_validation_error_slot:
                    validation_reason: str | None = None
                    payload_details = validation_error.internal_payload.details
                    if payload_details is not None:
                        validation_reason = payload_details.get("reason")

                    setattr(
                        self.state,
                        "last_validation_error",
                        validation_reason or validation_error.internal_payload.message,
                    )

                has_retries_remaining = attempt_number <= self.validation_max_retries
                if has_retries_remaining:
                    attempt_number += 1
                    continue

                raise WorkflowStepRetryExhaustedError(
                    step_name=self.name,
                    max_retries=self.validation_max_retries,
                    last_error_code=validation_error.internal_payload.code,
                    last_error_message=validation_error.internal_payload.message,
                ) from validation_error

            self.has_executed = True
            self.result = result
            has_validation_error_slot = hasattr(self.state, "last_validation_error")
            if has_validation_error_slot:
                setattr(self.state, "last_validation_error", None)
            return result

    @abstractmethod
    def execute_logic(self) -> O | Awaitable[O]:
        raise NotImplementedError

    async def _run_validators(self, *, result: O, attempt_number: int) -> None:
        for index, validator in enumerate(self.validators, start=1):
            validator_name = getattr(validator, "__name__", f"validator_{index}")
            try:
                validation_result = validator(self.state, result)
                if inspect.isawaitable(validation_result):
                    await validation_result
            except Exception as error:
                raise WorkflowStepValidationFailedError(
                    step_name=self.name,
                    validator_name=validator_name,
                    attempt_number=attempt_number,
                    reason=str(error),
                ) from error

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


class FunctionWorkflowStep[S: BaseModel, O: BaseModel | str, D](WorkflowStep[S, O, D]):
    def __init__(
        self,
        *,
        state: S,
        run: StepFunction[S, O, D],
        name: str | None = None,
    ) -> None:
        super().__init__(state=state, name=name)
        self._run = run

    def execute_logic(self) -> O | Awaitable[O]:
        return self._run(self.state, self.agent)
