from __future__ import annotations

import inspect
from collections.abc import Mapping
from enum import Enum
from types import NoneType
from types import UnionType
from typing import Callable, Literal, Union, get_args, get_origin, get_type_hints


class ToolSchemaMixin[O]:
    """Build JSON schema definitions from a tool ``__call__`` signature."""

    __call__: Callable[..., O]

    @property
    def json_schema(self) -> dict[str, object]:
        signature = inspect.signature(self.__call__)
        type_hints = get_type_hints(self.__call__)

        properties: dict[str, object] = {}
        required: list[str] = []

        for parameter_name, parameter in signature.parameters.items():
            if parameter_name in {"self", "cls", "ctx"}:
                continue

            is_variadic_parameter = parameter.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }
            if is_variadic_parameter:
                continue

            annotation = type_hints.get(parameter_name, object)
            properties[parameter_name] = self._build_schema_for_annotation(annotation)

            has_default_value = parameter.default is not inspect.Signature.empty
            if not has_default_value:
                required.append(parameter_name)

        json_schema: dict[str, object] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
            "required": required,
        }
        return json_schema

    def _build_schema_for_annotation(self, annotation: object) -> dict[str, object]:
        origin = get_origin(annotation)
        args = get_args(annotation)

        if annotation is bool:
            return {"type": "boolean"}
        if annotation is int:
            return {"type": "integer"}
        if annotation is float:
            return {"type": "number"}
        if annotation is str:
            return {"type": "string"}
        if annotation is NoneType:
            return {"type": "null"}

        if origin is list:
            item_annotation = args[0] if args else object
            return {
                "type": "array",
                "items": self._build_schema_for_annotation(item_annotation),
            }

        if origin is dict:
            return {"type": "object"}

        if origin is Mapping:
            return {"type": "object"}

        is_union_type = origin in {Union, UnionType}
        if is_union_type and args:
            non_none_types = [argument for argument in args if argument is not NoneType]
            is_nullable_union = len(non_none_types) != len(args)

            if len(non_none_types) == 1:
                single_schema = self._build_schema_for_annotation(non_none_types[0])
                if is_nullable_union:
                    single_schema["nullable"] = True
                return single_schema

            union_schema: dict[str, object] = {
                "oneOf": [
                    self._build_schema_for_annotation(argument)
                    for argument in non_none_types
                ]
            }
            if is_nullable_union:
                union_schema["nullable"] = True
            return union_schema

        if origin is Literal:
            literal_values = list(args)
            literal_schema: dict[str, object] = {"enum": literal_values}
            if literal_values:
                first_value = literal_values[0]
                if isinstance(first_value, bool):
                    literal_schema["type"] = "boolean"
                elif isinstance(first_value, int):
                    literal_schema["type"] = "integer"
                elif isinstance(first_value, float):
                    literal_schema["type"] = "number"
                elif isinstance(first_value, str):
                    literal_schema["type"] = "string"
            return literal_schema

        if inspect.isclass(annotation) and issubclass(annotation, Enum):
            enum_values = [member.value for member in annotation]
            enum_schema: dict[str, object] = {"enum": enum_values}
            if enum_values:
                first_enum_value = enum_values[0]
                if isinstance(first_enum_value, bool):
                    enum_schema["type"] = "boolean"
                elif isinstance(first_enum_value, int):
                    enum_schema["type"] = "integer"
                elif isinstance(first_enum_value, float):
                    enum_schema["type"] = "number"
                elif isinstance(first_enum_value, str):
                    enum_schema["type"] = "string"
            return enum_schema

        return {"type": "object"}
