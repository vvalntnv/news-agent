from __future__ import annotations

from collections.abc import Sequence
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain.ai.protocols import DependenciesType, Tool, Toolset


class ModelSettings(BaseModel):
    """Mirror of the Pydantic Agent's ``ModelSettings`` for per-model knobs."""

    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(1.0, ge=0.0, le=2.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(512, ge=1)
    timeout_seconds: float = Field(60.0, gt=0.0)
    stop_sequences: list[str] = Field(default_factory=list)
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    seed: int | None = None
    logit_bias: dict[str, int] = Field(default_factory=dict)
    parallel_tool_calls: bool = False
    extra_headers: dict[str, str] = Field(default_factory=dict)
    extra_body: dict[str, object] | None = None


class UsageLimits(BaseModel):
    """Usage caps mirroring the agent-level ``UsageLimits`` on ai.pydantic.dev."""

    model_config = ConfigDict(extra="forbid")

    request_limit: int | None = Field(50, ge=1)
    tool_calls_limit: int | None = None
    input_tokens_limit: int | None = None
    output_tokens_limit: int | None = None
    total_tokens_limit: int | None = None
    count_tokens_before_request: bool = False


class AIConfiguration(BaseModel):
    """Agent configuration inspired by the Pydantic Agent builder.

    ``ModelSettings`` mirrors the per-model knobs in ``backend/core/config.py``,
    so those values should only be provided to override the catalog defaults.
    """

    model_config = ConfigDict(extra="forbid")

    model_name: str
    provider_name: str | None = None
    model_alias: str | None = None
    agent_name: str | None = None
    instructions: str | Sequence[str] | None = None
    system_prompt: Sequence[str] = Field(default_factory=list)
    model_settings: ModelSettings = Field(default_factory=lambda: ModelSettings())
    retries: int = Field(default=1, ge=1)
    output_retries: int | None = None
    end_strategy: Literal["early", "exhaustive"] = "early"
    usage_limits: UsageLimits | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    tools: list[Tool] = Field(default_factory=list)
    toolsets: list[Toolset] = Field(default_factory=list)
    tool_timeout_seconds: float | None = None
    deps: DependenciesType | None = None
    deps_factory: Callable[[], DependenciesType] | None = None
    output_type: type[str] | type[BaseModel] = str
