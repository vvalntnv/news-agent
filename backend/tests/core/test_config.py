from core.config import Config, ModelConfigs


def test_model_configs_support_provider_and_model_lookup() -> None:
    config = Config(
        models={
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "settings": {
                        "enabled": True,
                        "api_key": "test-key",
                        "api_base_url": "https://api.openai.com/v1",
                    },
                    "default_model": "primary",
                    "models": {
                        "primary": {
                            "model_name": "gpt-4o-mini",
                            "temperature": 0.3,
                            "max_tokens": 256,
                        },
                        "fallback": {
                            "model_name": "gpt-4.1-mini",
                            "temperature": 0.2,
                            "max_tokens": 128,
                        },
                    },
                }
            },
        }
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
        model_alias="fallback",
    )
    assert fallback_model is not None
    assert fallback_model.model_name == "gpt-4.1-mini"


def test_model_configs_returns_none_for_unknown_provider_or_model() -> None:
    model_configs = ModelConfigs()

    unknown_provider = model_configs.get_provider("unknown")
    unknown_model = model_configs.get_model(provider_name="unknown")

    assert unknown_provider is None
    assert unknown_model is None
