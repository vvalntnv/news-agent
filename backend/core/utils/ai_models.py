from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from domain.ai.configuration import AIConfiguration
from core.config import (
    ModelConfigs,
    ModelDefinition,
    ProviderSettings,
    config as global_conf,
)


@dataclass(frozen=True)
class ResolvedModelConfig:
    provider_name: str
    provider_settings: ProviderSettings
    model_definition: ModelDefinition
    model_alias: str


def resolve_ai_model_config(agent_config: AIConfiguration) -> ResolvedModelConfig:
    models_config = global_conf.models
    if models_config is None:
        raise RuntimeError("AI provider catalog is not configured")

    provider_name, model_alias = _resolve_provider_and_alias(
        agent_config, models_config
    )

    provider_config = models_config.get_provider(provider_name)
    if provider_config is None:
        raise RuntimeError(f"provider '{provider_name}' is not available")

    model_definition = models_config.get_model(
        provider_name=provider_name,
        model_name_or_alias=model_alias
        or agent_config.model_alias
        or agent_config.model_name,
    )

    if model_definition is None:
        candidate_alias = model_alias or provider_config.default_model
        raise RuntimeError(
            f"model '{candidate_alias}' is not configured for provider '{provider_name}'"
        )

    resolved_alias = (
        model_alias or provider_config.default_model or model_definition.model_name
    )

    return ResolvedModelConfig(
        provider_name=provider_name,
        provider_settings=provider_config.settings,
        model_definition=model_definition,
        # FIX: This naming can cause confusion
        model_alias=resolved_alias,
    )


def _resolve_provider_and_alias(
    agent_config: AIConfiguration, models_config: ModelConfigs
) -> Tuple[str, str | None]:
    provider_candidate = agent_config.provider_name or models_config.default_provider
    alias_candidate = agent_config.model_alias
    raw_model_name = agent_config.model_name

    if not raw_model_name and provider_candidate is None:
        raise RuntimeError("AI configuration must include a non-empty model_name")

    provider_from_model: str | None = None

    if raw_model_name and "/" in raw_model_name:
        raw_provider, raw_alias = raw_model_name.strip().split("/", maxsplit=1)
        raw_provider = raw_provider.strip()
        raw_alias = raw_alias.strip()

        if raw_provider:
            provider_from_model = raw_provider

    provider_name = provider_candidate or provider_from_model

    if provider_name is None:
        raise RuntimeError("unable to resolve AI provider name")

    return provider_name, alias_candidate
