from typing import Self

from pydantic import BaseModel

from application.ai.workflow.step import (
    ConditionFunction,
    FunctionWorkflowStep,
    StepFunction,
    StepValidator,
    WorkflowStep,
)
from application.ai.workflow.workflow import (
    DependencyProvider,
    ResultResolver,
    Workflow,
)
from domain.ai.protocols import Agent


class WorkflowBuilder[S: BaseModel, O: BaseModel | str, D]:
    def __init__(self) -> None:
        self._initial_step: WorkflowStep[S, O, D] | None = None
        self._agent: Agent[O, D] | None = None
        self._workflow_name: str | None = None
        self._dependency_provider: DependencyProvider[S, D] | None = None
        self._result_resolver: ResultResolver[S, O] | None = None
        self._max_steps: int | None = None
        self._callable_steps: dict[
            StepFunction[S, O, D],
            FunctionWorkflowStep[S, O, D],
        ] = {}

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

        return Workflow(
            step_graph_entry=self._initial_step,
            agent=self._agent,
            workflow_name=self._workflow_name,
            dependency_provider=self._dependency_provider,
            result_resolver=self._result_resolver,
            max_steps=self._max_steps,
        )

    def set_workflow_name(self, workflow_name: str) -> Self:
        self._workflow_name = workflow_name
        return self

    def with_dependencies(self, dependencies: D) -> Self:
        self._dependency_provider = lambda _: dependencies
        return self

    def with_dependency_provider(
        self,
        dependency_provider: DependencyProvider[S, D],
    ) -> Self:
        self._dependency_provider = dependency_provider
        return self

    def with_result_resolver(self, resolver: ResultResolver[S, O]) -> Self:
        self._result_resolver = resolver
        return self

    def with_max_steps(self, max_steps: int) -> Self:
        if max_steps <= 0:
            raise ValueError("Workflow max steps must be positive")

        self._max_steps = max_steps
        return self

    def add_default_agent(self, agent: Agent[O, D]) -> Self:
        """
        Adds a default agent. If a step does not have an assigned agent to itself, the
        default agent will be applied to that particular step
        """
        self._agent = agent
        return self

    def add_starting_step(
        self,
        initial_step: WorkflowStep[S, O, D] | StepFunction[S, O, D],
    ) -> Self:
        if self._initial_step is not None:
            raise ValueError("The workflow already has a starting step")

        resolved_step = (
            self._get_function_workflow_step(initial_step)
            if callable(initial_step)
            else initial_step
        )

        self._initial_step = resolved_step
        return self

    def add_step(
        self,
        start: WorkflowStep[S, O, D] | StepFunction[S, O, D],
        end: WorkflowStep[S, O, D] | StepFunction[S, O, D],
    ) -> Self:
        start_step = (
            self._get_function_workflow_step(start) if callable(start) else start
        )
        end_step = self._get_function_workflow_step(end) if callable(end) else end

        start_step.add_direct_transition(end_step)
        return self

    def add_transition(
        self,
        premise: WorkflowStep[S, O, D] | StepFunction[S, O, D],
        condition_func: ConditionFunction[S],
        consequence: WorkflowStep[S, O, D] | StepFunction[S, O, D],
    ) -> Self:
        premise_step = (
            self._get_function_workflow_step(premise) if callable(premise) else premise
        )

        consequence_step = (
            self._get_function_workflow_step(consequence)
            if callable(consequence)
            else consequence
        )

        premise_step.add_transition(condition_func, consequence_step)
        return self

    def register_function_step(
        self,
        *,
        state: S,
        function: StepFunction[S, O, D],
        name: str | None = None,
    ) -> Self:
        workflow_function = FunctionWorkflowStep(
            state=state,
            run=function,
            name=name or function.__name__,
        )

        self._callable_steps[function] = workflow_function
        return self

    def create_function_step(
        self,
        *,
        state: S,
        run: StepFunction[S, O, D],
        name: str | None = None,
    ) -> FunctionWorkflowStep[S, O, D]:
        return FunctionWorkflowStep(state=state, run=run, name=name)

    def create_callable_step(
        self,
        *,
        state: S,
        run: StepFunction[S, O, D],
        name: str | None = None,
    ) -> FunctionWorkflowStep[S, O, D]:
        return self.create_function_step(state=state, run=run, name=name)

    def add_validator(
        self,
        step: WorkflowStep[S, O, D] | StepFunction[S, O, D],
        validator: StepValidator[S, O],
    ) -> Self:
        resolved_step = (
            self._get_function_workflow_step(step) if callable(step) else step
        )
        resolved_step.add_validator(validator)
        return self

    def set_step_validation_retries(
        self,
        step: WorkflowStep[S, O, D] | StepFunction[S, O, D],
        max_retries: int,
    ) -> Self:
        resolved_step = (
            self._get_function_workflow_step(step) if callable(step) else step
        )
        resolved_step.set_validation_retries(max_retries)
        return self

    def _get_function_workflow_step(
        self,
        function: StepFunction[S, O, D],
    ) -> FunctionWorkflowStep[S, O, D]:
        cached_step = self._callable_steps.get(function, None)
        if cached_step is not None:
            return cached_step

        raise Exception(
            "Function workflow step not registered in the builder! Please use the .register_function_step method to register this funciton"
        )
