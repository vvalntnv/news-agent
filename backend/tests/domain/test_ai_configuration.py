import pytest

from pydantic import ValidationError

from domain.ai.configuration import AIConfiguration


def test_ai_configuration_defaults() -> None:
    config = AIConfiguration(model_name="test-model")

    assert config.model_settings.temperature == 1.0
    assert config.model_settings.top_p == 1.0
    assert config.model_settings.max_tokens == 512
    assert config.model_settings.timeout_seconds == 60.0
    assert config.model_settings.stop_sequences == []


def test_ai_configuration_rejects_invalid_temperature() -> None:
    with pytest.raises(ValidationError):
        AIConfiguration(model_name="test-model", model_settings={"temperature": -0.1})


def test_stop_sequences_list_isolated() -> None:
    first = AIConfiguration(model_name="foo")
    second = AIConfiguration(model_name="foo")

    first.model_settings.stop_sequences.append("END")

    assert second.model_settings.stop_sequences == []
