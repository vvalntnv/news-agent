from __future__ import annotations

import pytest

from core.config import (
    ModelConfigs,
    ModelDefinition,
    ProviderModelsConfig,
    ProviderSettings,
    config as global_config,
)
from core.errors import InternalError
from core.utils.ai_models import resolve_ai_model_config
from domain.ai.configuration import AIConfiguration


def _build_model_catalog() -> ModelConfigs:
    return ModelConfigs(
        default_provider="openai",
        providers={
            "openai": ProviderModelsConfig(
                settings=ProviderSettings(),
                default_model="primary",
                models={
                    "primary": ModelDefinition(
                        model_name="gpt-4",
                        temperature=0.2,
                        top_p=1.0,
                        max_tokens=128,
                        timeout_seconds=30.0,
                    )
                },
            ),
            "anthropic": ProviderModelsConfig(
                settings=ProviderSettings(),
                default_model="claude-main",
                models={
                    "claude-main": ModelDefinition(
                        model_name="claude-3-7-sonnet",
                        temperature=0.2,
                        top_p=1.0,
                        max_tokens=128,
                        timeout_seconds=30.0,
                    )
                },
            ),
        },
    )


def test_resolve_ai_model_config_accepts_matching_prefixed_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(global_config, "models", _build_model_catalog())

    ai_config: AIConfiguration[str, None] = AIConfiguration(
        provider_name="openai",
        model_name="openai:gpt-4",
        output_type=str,
    )

    resolved = resolve_ai_model_config(ai_config)

    assert resolved.provider_name == "openai"
    assert resolved.model_definition.model_name == "gpt-4"


def test_resolve_ai_model_config_rejects_mismatched_prefixed_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(global_config, "models", _build_model_catalog())

    ai_config: AIConfiguration[str, None] = AIConfiguration(
        provider_name="anthropic",
        model_name="openai:gpt-4",
        output_type=str,
    )

    with pytest.raises(InternalError) as raised_error:
        resolve_ai_model_config(ai_config)

    assert raised_error.value.internal_payload.code == "ai_provider_mismatch"
    assert raised_error.value.internal_payload.details == {
        "provider_name": "anthropic",
        "model_name_provider": "openai",
    }
