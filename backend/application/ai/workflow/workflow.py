import inspect
from typing import Awaitable, Callable

from pydantic import BaseModel

from core.config import config
from core.errors import (
    WorkflowDependencyNotConfiguredError,
    WorkflowDependencyResolutionError,
    WorkflowLoopLimitExceededError,
    WorkflowNoResultError,
)
from application.ai.workflow.step import WorkflowStep
from domain.ai.protocols import Agent

type DependencyProvider[S: BaseModel, D] = Callable[[S], D | Awaitable[D]]
type ResultResolver[S: BaseModel, O: BaseModel | str] = Callable[[S], O | Awaitable[O]]


class Workflow[S: BaseModel, O: BaseModel | str, D]:
    def __init__(
        self,
        step_graph_entry: WorkflowStep[S, O, D],
        agent: Agent[O, D],
        workflow_name: str | None = None,
        dependency_provider: DependencyProvider[S, D] | None = None,
        result_resolver: ResultResolver[S, O] | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.entrypoint: WorkflowStep[S, O, D]
        self.agent: Agent[O, D]
        self.entrypoint = step_graph_entry
        self.agent = agent
        self.workflow_name = workflow_name or self.__class__.__name__
        self.dependency_provider = dependency_provider
        self.result_resolver = result_resolver
        self.max_steps = max_steps or config.workflow_max_execution_steps

    async def execute_workflow(self) -> O:
        final_result: O | None = None
        current_step: WorkflowStep[S, O, D] | None = self.entrypoint
        executed_steps_count = 0

        while current_step is not None:
            has_exceeded_max_steps = executed_steps_count >= self.max_steps
            if has_exceeded_max_steps:
                raise WorkflowLoopLimitExceededError(
                    workflow_name=self.workflow_name,
                    max_steps=self.max_steps,
                    step_name=current_step.name,
                )

            if not current_step.has_agent_assigned:
                current_step.set_agent(self.agent)

            step_dependency = await self._resolve_dependency(current_step)
            if step_dependency is not None:
                current_step.agent.add_dependency(step_dependency)

            result = await current_step.execute()
            final_result = result
            current_step = current_step.get_next()
            executed_steps_count += 1

        if self.result_resolver is not None:
            resolved_result = self.result_resolver(self.entrypoint.state)
            return (
                await resolved_result
                if inspect.isawaitable(resolved_result)
                else resolved_result
            )

        if final_result is None:
            raise WorkflowNoResultError(workflow_name=self.workflow_name)

        return final_result

    async def _resolve_dependency(self, step: WorkflowStep[S, O, D]) -> D | None:
        if self.dependency_provider is None:
            return None

        try:
            dependency_result = self.dependency_provider(step.state)
            dependency = (
                await dependency_result
                if inspect.isawaitable(dependency_result)
                else dependency_result
            )
        except Exception as error:
            raise WorkflowDependencyResolutionError(
                workflow_name=self.workflow_name,
                step_name=step.name,
                reason=str(error),
            ) from error

        if dependency is None:
            raise WorkflowDependencyNotConfiguredError(
                workflow_name=self.workflow_name,
                step_name=step.name,
            )

        return dependency
