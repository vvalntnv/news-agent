from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AIConfiguration(BaseModel):
    """Configuration values shared by any AI-backed agent."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    provider_name: str | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    api_version: str | None = None
    temperature: float = Field(1.0, ge=0.0, le=2.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(512, ge=1)
    timeout_seconds: float = Field(60.0, gt=0.0)
    stop_sequences: list[str] = Field(default_factory=list)
    metadata: dict[str, str] | None = None
