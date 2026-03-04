from pathlib import Path

import yaml


class ModelConfigurationLoader:
    def __init__(self, file_path: Path | None = None) -> None:
        self._file_path = file_path or self._resolve_default_file_path()

    def load(self) -> dict[str, object] | None:
        configuration_exists = self._file_path.exists()
        if not configuration_exists:
            return None

        with self._file_path.open("r", encoding="utf-8") as file_handle:
            parsed_yaml: object = yaml.safe_load(file_handle)

        if parsed_yaml is None:
            return None

        is_dictionary_payload = isinstance(parsed_yaml, dict)
        if not is_dictionary_payload:
            raise ValueError(
                f"Invalid model configuration at '{self._file_path}': "
                "top-level YAML value must be a mapping"
            )

        return dict(parsed_yaml)

    @staticmethod
    def _resolve_default_file_path() -> Path:
        backend_directory = Path(__file__).resolve().parent.parent
        return backend_directory / "model_config.yaml"
