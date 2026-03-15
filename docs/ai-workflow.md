# AI Workflow Guide

This document describes the workflow engine in `backend/application/ai/workflow`.

## Purpose

The workflow layer executes AI-driven, multi-step flows with:

- step transitions,
- step-level validators,
- dependency injection for agents,
- execution safety guards,
- explicit final-result resolution.

## Core Types

### `WorkflowStep[S, O, D]`

Base class for graph steps.

- `execute_logic() -> O | Awaitable[O]` defines step behavior.
- `add_direct_transition(next_step)` creates a fixed edge.
- `add_transition(condition, next_step)` creates conditional edges.
- `add_validator(validator)` adds a validator for this step only.
- `set_validation_retries(max_retries)` configures validator retry count.

Validation flow:

1. Step logic runs.
2. Validators run in order.
3. If validation fails, the step reruns until validation passes or retry budget is exhausted.
4. Exhaustion raises `WorkflowStepRetryExhaustedError`.

### `FunctionWorkflowStep[S, O, D]`

Callable-based step implementation for lightweight workflow definitions.

Use when subclassing `WorkflowStep` is unnecessary.

### `Workflow[S, O, D]`

Workflow executor.

- Injects default agent into steps when missing.
- Resolves and injects dependencies per-step via dependency provider.
- Enforces `max_steps` loop safety guard.
- Returns either:
  - `result_resolver(state)` if provided,
  - or the latest step result.

## Builder API

`WorkflowBuilder` configures and builds workflows.

Key methods:

- `add_default_agent(agent)`
- `add_starting_step(step)` / `initialize(step)`
- `add_step(start, end)`
- `add_transition(premise, condition, consequence)`
- `add_function_step(state=..., run=..., name=..., start=...)`
- `add_validator(step, validator)`
- `set_step_validation_retries(step, max_retries)`
- `with_dependencies(dependencies)`
- `with_dependency_provider(provider)`
- `with_result_resolver(resolver)`
- `with_max_steps(max_steps)`
- `set_workflow_name(name)`

## Configurable Runtime Settings

Configured in `backend/core/config.py`:

- `workflow_step_default_validation_retries`
- `workflow_max_execution_steps`

## Errors

Workflow failures raise typed internal errors in `backend/core/errors/workflow_related.py`:

- `WorkflowDependencyNotConfiguredError`
- `WorkflowDependencyResolutionError`
- `WorkflowStepValidationFailedError`
- `WorkflowStepRetryExhaustedError`
- `WorkflowLoopLimitExceededError`
- `WorkflowNoResultError`

These follow the shared `InternalError` + `ErrorPayload` contract.

## Predefined Workflow Notes

`news_site_exploration` now:

- uses workflow-level dependency provider (`state -> NewsSiteExplorationDependencies`),
- validates article-level selector output with step validators,
- enforces strict `mainArticleContainer` semantics across sampled article URLs (exactly one match per sample, minimum text/paragraph content, low link density),
- retries validation failures at step level based on `max_attempts`,
- resolves final output from workflow state via explicit resolver.
