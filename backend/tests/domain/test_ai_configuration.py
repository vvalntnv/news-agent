import pytest

from pydantic import ValidationError

from domain.ai.configuration import AIConfiguration, ModelSettings


def test_ai_configuration_defaults() -> None:
    config: AIConfiguration[str, None] = AIConfiguration(
        model_name="test-model",
        output_type=str,
    )

    assert config.model_settings.temperature == 0.2
    assert config.model_settings.top_p == 1.0
    assert config.model_settings.max_tokens == 512
    assert config.model_settings.timeout_seconds == 60.0
    assert config.model_settings.stop_sequences == []


def test_ai_configuration_rejects_invalid_temperature() -> None:
    with pytest.raises(ValidationError):
        AIConfiguration[str, None](
            model_name="test-model",
            output_type=str,
            model_settings=ModelSettings(
                temperature=-0.1,
                top_p=1.0,
                max_tokens=512,
                timeout_seconds=60.0,
            ),
        )


def test_stop_sequences_list_isolated() -> None:
    first: AIConfiguration[str, None] = AIConfiguration(
        model_name="foo",
        output_type=str,
    )
    second: AIConfiguration[str, None] = AIConfiguration(
        model_name="foo",
        output_type=str,
    )

    first.model_settings.stop_sequences.append("END")

    assert second.model_settings.stop_sequences == []
