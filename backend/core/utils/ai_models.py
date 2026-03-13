from __future__ import annotations

from dataclasses import dataclass

from core.config import (
    ModelConfigs,
    ModelDefinition,
    ProviderSettings,
    config as global_conf,
)
from core.errors import ErrorPayload, InternalError
from domain.ai.configuration import AIConfiguration


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
        model_name_or_alias=model_alias,
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
        model_alias=resolved_alias,
    )


def _resolve_provider_and_alias(
    agent_config: AIConfiguration, models_config: ModelConfigs
) -> tuple[str, str | None]:
    provider_candidate = agent_config.provider_name or models_config.default_provider
    alias_candidate = agent_config.model_alias
    raw_model_name = _normalize_string_value(agent_config.model_name)

    if not raw_model_name and provider_candidate is None:
        raise RuntimeError("AI configuration must include a non-empty model_name")

    provider_from_model, model_alias_from_name = _extract_provider_and_model(
        raw_model_name, models_config
    )

    has_provider_conflict = (
        provider_candidate is not None
        and provider_from_model is not None
        and provider_candidate != provider_from_model
    )
    if has_provider_conflict:
        raise InternalError(
            internal_payload=ErrorPayload(
                code="ai_provider_mismatch",
                message="AI model provider in model_name does not match provider_name.",
                details={
                    "provider_name": provider_candidate,
                    "model_name_provider": provider_from_model,
                },
            )
        )

    provider_name = provider_candidate or provider_from_model

    if provider_name is None:
        raise RuntimeError("unable to resolve AI provider name")

    resolved_model_alias = alias_candidate or model_alias_from_name

    return provider_name, resolved_model_alias


def _extract_provider_and_model(
    raw_model_name: str | None,
    models_config: ModelConfigs,
) -> tuple[str | None, str | None]:
    if raw_model_name is None:
        return None, None

    if ":" in raw_model_name:
        raw_provider, raw_alias = raw_model_name.split(":", maxsplit=1)
        provider_name = _normalize_string_value(raw_provider)
        model_alias = _normalize_string_value(raw_alias)
        return provider_name, model_alias

    if "/" in raw_model_name:
        raw_provider, raw_alias = raw_model_name.split("/", maxsplit=1)
        provider_name = _normalize_string_value(raw_provider)
        model_alias = _normalize_string_value(raw_alias)
        if provider_name in models_config.providers:
            return provider_name, model_alias

    return None, raw_model_name


def _normalize_string_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    if normalized_value == "":
        return None

    return normalized_value
