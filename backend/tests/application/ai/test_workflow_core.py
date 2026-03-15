from collections.abc import AsyncIterable, Callable

import pytest
from pydantic import BaseModel

from application.ai.workflow.builder import WorkflowBuilder
from application.ai.workflow.state import WorkflowState
from core.errors import WorkflowLoopLimitExceededError
from domain.ai.protocols import Agent

pytestmark = pytest.mark.anyio


class _WorkflowState(WorkflowState):
    counter: int = 0


class _WorkflowDependency(BaseModel):
    value: str


class _StringAgent:
    output_type = str
    dependencies_type = _WorkflowDependency
    history_tracker: Callable[[list[object]], list[object]] = staticmethod(
        lambda messages: messages
    )
    tools: list[object] = []

    def __init__(self) -> None:
        self.dependencies: _WorkflowDependency | None = None

    def add_dependency(self, dependency: _WorkflowDependency) -> "_StringAgent":
        self.dependencies = dependency
        return self

    async def run(self, prompt: str) -> str:
        _ = prompt
        if self.dependencies is None:
            raise AssertionError("Expected workflow dependency to be injected")

        return self.dependencies.value

    async def stream(self, prompt: str) -> AsyncIterable[str]:
        if False:
            yield prompt


async def test_step_validator_retries_until_validation_passes() -> None:
    state = _WorkflowState()
    step = WorkflowBuilder[
        _WorkflowState, str, _WorkflowDependency
    ]().create_callable_step(
        state=state,
        run=lambda local_state, _agent: _run_increment_step(local_state),
        name="increment_step",
    )

    step.add_validator(_validate_counter_reached_two)
    step.set_validation_retries(1)

    workflow = (
        WorkflowBuilder[_WorkflowState, str, _WorkflowDependency]
        .initialize(step)
        .add_default_agent(_StringAgent())
        .build()
    )

    result = await workflow.execute_workflow()

    assert result == "count=2"
    assert state.counter == 2


async def test_workflow_dependency_provider_injects_dependencies() -> None:
    state = _WorkflowState(counter=7)

    async def _run_with_agent(
        _state: _WorkflowState,
        agent: Agent[str, _WorkflowDependency],
    ) -> str:
        return await agent.run("dependency-check")

    step = WorkflowBuilder[
        _WorkflowState, str, _WorkflowDependency
    ]().create_callable_step(
        state=state,
        run=_run_with_agent,
        name="dependency_step",
    )

    workflow = (
        WorkflowBuilder[_WorkflowState, str, _WorkflowDependency]
        .initialize(step)
        .add_default_agent(_StringAgent())
        .with_dependency_provider(
            lambda local_state: _WorkflowDependency(value=f"deps-{local_state.counter}")
        )
        .build()
    )

    result = await workflow.execute_workflow()

    assert result == "deps-7"


async def test_workflow_stops_when_loop_limit_is_exceeded() -> None:
    state = _WorkflowState()
    step = WorkflowBuilder[
        _WorkflowState, str, _WorkflowDependency
    ]().create_callable_step(
        state=state,
        run=lambda _state, _agent: "loop",
        name="loop_step",
    )
    step.add_direct_transition(step)

    workflow = (
        WorkflowBuilder[_WorkflowState, str, _WorkflowDependency]
        .initialize(step)
        .add_default_agent(_StringAgent())
        .with_max_steps(2)
        .build()
    )

    with pytest.raises(WorkflowLoopLimitExceededError):
        await workflow.execute_workflow()


def _run_increment_step(state: _WorkflowState) -> str:
    state.counter += 1
    return f"count={state.counter}"


def _validate_counter_reached_two(state: _WorkflowState, _result: str) -> None:
    if state.counter >= 2:
        return

    raise ValueError("counter is not high enough")
