from __future__ import annotations

from enum import StrEnum
from typing import Literal

from domain.ai.tool_schema_mixin import ToolSchemaMixin


class _MathTool(ToolSchemaMixin):
    def __call__(self, a: int, b: int, label: str | None = None) -> int:
        return a + b


class _Mode(StrEnum):
    FAST = "fast"
    SAFE = "safe"


class _ModeTool(ToolSchemaMixin):
    def __call__(self, mode: _Mode, detail: Literal["short", "long"]) -> str:
        return f"{mode}:{detail}"


def test_build_json_schema_from_call_handles_required_and_optional_fields() -> None:
    tool = _MathTool()

    json_schema = tool.build_json_schema_from_call()

    assert json_schema["type"] == "object"
    assert json_schema["additionalProperties"] is False
    assert json_schema["required"] == ["a", "b"]

    properties = json_schema["properties"]
    assert isinstance(properties, dict)
    assert properties["a"] == {"type": "integer"}
    assert properties["b"] == {"type": "integer"}
    assert properties["label"] == {"type": "string", "nullable": True}


def test_build_json_schema_from_call_supports_enum_and_literal() -> None:
    tool = _ModeTool()

    json_schema = tool.build_json_schema_from_call()

    properties = json_schema["properties"]
    assert isinstance(properties, dict)
    assert properties["mode"] == {"type": "string", "enum": ["fast", "safe"]}
    assert properties["detail"] == {"type": "string", "enum": ["short", "long"]}
