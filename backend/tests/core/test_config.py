from core.config import (
    Config,
    ModelConfigs,
    ModelDefinition,
    ProviderModelsConfig,
    ProviderSettings,
)


def test_model_configs_support_provider_and_model_lookup() -> None:
    model_configs = ModelConfigs(
        default_provider="openai",
        providers={
            "openai": ProviderModelsConfig(
                settings=ProviderSettings(
                    enabled=True,
                    api_key="test-key",
                    api_base_url="https://api.openai.com/v1",
                    timeout_seconds=60.0,
                    max_retries=2,
                ),
                default_model="primary",
                models={
                    "primary": ModelDefinition(
                        model_name="gpt-4o-mini",
                        temperature=0.3,
                        top_p=1.0,
                        max_tokens=256,
                        timeout_seconds=60.0,
                    ),
                    "fallback": ModelDefinition(
                        model_name="gpt-4.1-mini",
                        temperature=0.2,
                        top_p=1.0,
                        max_tokens=128,
                        timeout_seconds=60.0,
                    ),
                },
            )
        },
    )

    config = Config(
        models=model_configs,
    )

    assert config.models is not None
    assert config.models.default_provider == "openai"

    provider = config.models.get_provider("openai")
    assert provider is not None
    assert provider.settings.api_key == "test-key"

    default_model = config.models.get_model(provider_name="openai")
    assert default_model is not None
    assert default_model.model_name == "gpt-4o-mini"

    fallback_model = config.models.get_model(
        provider_name="openai",
        model_name_or_alias="fallback",
    )
    assert fallback_model is not None
    assert fallback_model.model_name == "gpt-4.1-mini"


def test_model_configs_returns_none_for_unknown_provider_or_model() -> None:
    model_configs = ModelConfigs()

    unknown_provider = model_configs.get_provider("unknown")
    unknown_model = model_configs.get_model(provider_name="unknown")

    assert unknown_provider is None
    assert unknown_model is None
