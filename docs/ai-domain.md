# AI domain and implementation guide

This document describes the current AI architecture in `backend/domain/ai/` and `backend/infrastructure/ai/`.

It is intended to be the single knowledge base for:

- domain contracts and types,
- concrete pydantic-ai integration,
- dependency and tool-calling flow,
- known behavior and caveats,
- test coverage currently implemented.

## Design overview

The AI layer is split into two parts:

1. **Domain contracts (`domain/ai`)**
   - Defines provider-agnostic protocols and configuration models.
   - No concrete model provider calls happen here.

2. **Infrastructure implementation (`infrastructure/ai`)**
   - Adapts domain types to `pydantic_ai.Agent`.
   - Resolves model/provider information and creates runnable agents.
   - Maps project tools/toolsets into pydantic-ai tools.

The import root is `backend/`, so imports are done as `from domain...`, `from infrastructure...`, `from core...`.

## Domain layer (`backend/domain/ai`)

### `protocols.py`

Core protocols:

- `type HistoryTrackerFunc = Callable[[list[ModelMessage]], list[ModelMessage]]`
  - Signature used for history processors.
- `Tool[T, D]` protocol
  - Required fields: `name`, `description`, `json_schema`, `ctx`.
  - Required call shape: `__call__(**kwargs: object) -> T | Awaitable[T]`.
- `Toolset` protocol
  - Groups tools under `tools`, `name`, `description`.
- `Agent[O, D]` protocol
  - Required metadata: `output_type`, `dependencies_type`, `history_tracker`, `tools`.
  - Runtime methods:
    - `async run(prompt: str) -> O`
    - `stream(prompt: str) -> AsyncIterable[str]`
- `AIFactory` protocol
  - `create_agent(config: AIConfiguration[O, D]) -> Agent[O, D]`

Note: `AIConfiguration` is imported under `TYPE_CHECKING` to avoid runtime circular imports.

### `configuration.py`

Pydantic models that define all tunable AI settings.

#### `ModelSettings`

Mirrors pydantic-ai model settings and validates key generation-time values:

- Sampling/limits: `temperature`, `top_p`, `max_tokens`, `timeout_seconds`
- Output shaping: `stop_sequences`
- Optional penalties/seeding: `presence_penalty`, `frequency_penalty`, `seed`
- Tool behavior and request-level metadata:
  - `parallel_tool_calls`
  - `logit_bias`
  - `extra_headers`
  - `extra_body`

Helper:

- `reasonable_model_settings()` returns validated defaults.

#### `UsageLimits`

Request/token/tool-call limit model:

- `request_limit`, `tool_calls_limit`, `input_tokens_limit`, `output_tokens_limit`, `total_tokens_limit`
- `count_tokens_before_request`

#### `AIConfiguration[O, D]`

Main agent construction payload:

- Model identity: `model_name`, `provider_name`, `model_alias`
- Agent identity/prompts: `agent_name`, `instructions`, `system_prompt`
- Retry/termination controls: `retries`, `output_retries`, `end_strategy`
- Metadata and limits: `metadata`, `usage_limits`
- Tooling: `tools`, `toolsets`, `tool_timeout_seconds`
- Dependencies: `deps`, `deps_factory`
- Output schema: `output_type` (`type[O]` or `type[str]`)

Model config:

- `extra="forbid"`
- `arbitrary_types_allowed=True` (required because `tools`/`toolsets` are protocol-typed)

### `tool_schema_mixin.py`

`ToolSchemaMixin` introspects a tool `__call__` signature and generates JSON schema.

Current conversion support includes:

- primitives: `bool`, `int`, `float`, `str`, `None`
- `list[T]`, `dict`, `Mapping`
- unions (`|` / `Union`) with nullable detection
- `Literal[...]`
- `Enum` subclasses

Behavior details:

- `self`/`cls` and variadic params are ignored
- required fields are inferred from parameters without default values
- unknown annotations fall back to `{"type": "object"}`

### `__init__.py`

Package exports:

- `Agent`
- `AIConfiguration`
- `AIFactory`
- `ToolSchemaMixin`

## Infrastructure layer (`backend/infrastructure/ai`)

### `agent.py` - `ProjectPydanticAgent[O, D]`

Concrete runtime wrapper around `pydantic_ai.Agent[D, O]`.

Construction data stored on wrapper:

- `_agent` (pydantic-ai agent)
- `output_type`
- `dependencies_type`
- `tools`
- `toolsets`
- `history_tracker`

Runtime methods:

- `add_dependency(dependency: D) -> Self`
  - Stores dependencies and returns self for fluent usage.
- `run(prompt: str) -> O`
  - Validates dependencies.
  - Calls underlying `_agent.run_stream_events(prompt, deps=self.dependencies)`.
  - Intercepts and logs all pydantic-ai events.
  - Returns final output from `AgentRunResultEvent.result.output`.
- `stream(prompt: str) -> AsyncIterable[str]`
  - Validates dependencies.
  - Uses `_agent.run_stream(..., event_stream_handler=...)` and yields `stream_text()` chunks.
  - Event stream handler is always attached and logs streamed events.

AI event logging:

- Uses `infrastructure/ai/event_logger.py` for event interception.
- Logs event lifecycle (`part_start`, `part_delta`, `part_end`, `tool_call`, `tool_result`, `final_result`, `run_result`).
- Logger source is `core/loggers` under the `news_agent.ai` logger namespace.

Dependency guard:

- Missing `dependencies` attribute raises `AssertionError("This class has no deps")`.
- Explicit `None` deps raises `AssertionError("The dependencies are not set!")`.
- Falsy but valid dependencies (for example `{}`) are accepted.

### `factory.py` - `PydanticAgentAIFactory`

Primary implementation of the domain `AIFactory` protocol.

#### `create_agent(config)` flow

1. Resolve model via `resolve_ai_model_config(config)`.
2. Map `config.tools` and `config.toolsets` to pydantic tools.
3. Resolve dependency type from `config.deps`.
4. Build concrete `pydantic_ai.Agent`.
5. Wrap in `ProjectPydanticAgent` and return as domain `Agent`.

#### Tool mapping

- Uses `PydanticTool.from_schema(...)`.
- Maps each tool with:
  - `function=tool.__call__`
  - `name`
  - `description`
  - `json_schema=dict(tool.json_schema)`
  - `takes_ctx=tool.ctx is not None`
- Toolsets are flattened into the same final list.

#### Settings mapping

`_map_model_settings(ModelSettings) -> PydanticModelSettings` maps:

- direct: `temperature`, `top_p`, `max_tokens`, `timeout`, `stop_sequences`, `logit_bias`, `parallel_tool_calls`, `extra_headers`, `extra_body`
- conditional keys only when set:
  - `presence_penalty`
  - `frequency_penalty`
  - `seed`

Collections are copied (`list(...)`, `dict(...)`) before passing to pydantic-ai.

#### Dependency type resolution

- `None` deps -> `type(None)`
- value present -> `type(value)`

#### Constructed pydantic-ai agent fields

`_construct_pydantic_agent(...)` forwards:

- model identity: `model`
- output and prompts: `output_type`, `instructions`, `system_prompt`
- dependency typing: `deps_type`
- agent metadata: `name`, `metadata`
- model behavior: `model_settings`, `retries`, `output_retries`, `end_strategy`
- tool execution: `tools`, `tool_timeout`
- history processing: `history_processors=[history_processor]`

### `history_processor.py` - `BasicHistoryProcessor`

Current behavior is intentionally minimal:

- Callable signature: `__call__(messages: list[ModelMessage]) -> list[ModelMessage]`
- Returns input messages unchanged.
- Includes a temporary print side effect.

This component is in active development and should be treated as unstable.

## Model resolution dependency

`PydanticAgentAIFactory` depends on `core.utils.ai_models.resolve_ai_model_config`.

This resolver:

- reads configured providers/models from `core.config.config.models`,
- resolves provider + alias from `AIConfiguration` (`provider_name`, `model_alias`, `model_name`),
- returns concrete `model_definition.model_name` used by `pydantic_ai.Agent(model=...)`.

## Tool-calling behavior in this architecture

From this project perspective:

1. Domain tool implementations expose `name`, `description`, `json_schema`, and `__call__`.
2. Factory maps them to pydantic-ai tools using `Tool.from_schema`.
3. During `run`, pydantic-ai may request a tool call.
4. Tool function executes locally.
5. Final model output is returned through `run_result.output`.

## Current tests for AI module

Implemented tests are in:

- `backend/tests/infrastructure/ai/test_agent.py`
- `backend/tests/infrastructure/ai/test_factory.py`

Covered scenarios:

- agent dependency lifecycle and guards
- agent `run` and `stream` forwarding
- factory wiring and return type construction
- model settings mapping and optional key behavior
- dependency type resolution
- tool and toolset mapping
- mocked model response path with dependencies
- mocked tool-calling path where the model requests a mapped tool

Not yet covered (intentionally):

- `BasicHistoryProcessor` behavior (under active development)

## Example usage

```python
from domain.ai.configuration import AIConfiguration
from infrastructure.ai.factory import PydanticAgentAIFactory

factory = PydanticAgentAIFactory()

config = AIConfiguration[str, dict[str, str]](
    model_name="openai/gpt-5.1-mini",
    output_type=str,
    instructions="Answer shortly.",
    deps={"tenant": "acme"},
)

agent = factory.create_agent(config)
agent = agent.add_dependency({"tenant": "acme"})
result = await agent.run("Give me a short update")
```

## Known caveats and follow-ups

- `deps_factory` exists in `AIConfiguration` but is not yet consumed by the factory.
- `usage_limits` is defined in config but not yet forwarded in `_construct_pydantic_agent`.
- `BasicHistoryProcessor` still contains temporary debug behavior.
