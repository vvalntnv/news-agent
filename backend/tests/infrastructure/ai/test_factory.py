from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable, cast
from unittest.mock import MagicMock

import pytest
from pydantic_ai import AgentRunResult, AgentRunResultEvent

from core.config import ModelDefinition, ProviderSettings
from core.utils.ai_models import ResolvedModelConfig
from domain.ai.configuration import AIConfiguration, ModelSettings
from domain.ai.protocols import Tool, Toolset
import infrastructure.ai.factory as factory_module
from infrastructure.ai.agent import ProjectPydanticAgent
from infrastructure.ai.factory import PydanticAgentAIFactory

pytestmark = pytest.mark.anyio


@dataclass
class _DependencyContainer:
    tenant_id: str


class _FakeTool:
    def __init__(self, *, name: str, ctx: object | None) -> None:
        self.name = name
        self.description = f"description for {name}"
        self.json_schema = {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "required": [],
        }
        self.ctx = ctx

    def __call__(self, **kwargs: object) -> str:
        del kwargs
        return "ok"


class _RecordingTool(_FakeTool):
    def __init__(self, *, name: str, ctx: object | None) -> None:
        super().__init__(name=name, ctx=ctx)
        self.calls: list[str] = []
        self.json_schema = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "additionalProperties": False,
            "required": ["text"],
        }

    def __call__(self, **kwargs: object) -> str:
        text_value = kwargs.get("text")
        assert isinstance(text_value, str)
        self.calls.append(text_value)
        return f"tool-echo:{text_value}"


class _FakeToolset:
    def __init__(self, tools: list[_FakeTool]) -> None:
        self.tools = tools
        self.name = "test-toolset"
        self.description = "toolset description"


class _ResultEventsIterator:
    def __init__(self, output: str) -> None:
        self._event = AgentRunResultEvent(AgentRunResult(output))
        self._yielded = False

    def __aiter__(self) -> AsyncIterator[AgentRunResultEvent[str]]:
        return self

    async def __anext__(self) -> AgentRunResultEvent[str]:
        if self._yielded:
            raise StopAsyncIteration

        self._yielded = True
        return self._event


def _build_configuration(
    *,
    tools: list[Tool] | None = None,
    toolsets: list[Toolset] | None = None,
    deps: _DependencyContainer | None = None,
    model_settings: ModelSettings | None = None,
) -> AIConfiguration[str, _DependencyContainer]:
    resolved_tools = tools if tools is not None else []
    resolved_toolsets = toolsets if toolsets is not None else []

    return AIConfiguration[str, _DependencyContainer](
        model_name="openai/gpt-5.1-mini",
        output_type=str,
        tools=resolved_tools,
        toolsets=resolved_toolsets,
        deps=deps,
        model_settings=model_settings or ModelSettings.reasonable_model_settings(),
        metadata={"env": "test"},
        instructions="Answer briefly",
        system_prompt=["Be concise"],
        retries=2,
        output_retries=3,
        tool_timeout_seconds=15.0,
    )


def _build_resolved_model_config() -> ResolvedModelConfig:
    return ResolvedModelConfig(
        provider_name="openai",
        provider_settings=ProviderSettings(timeout_seconds=60.0, max_retries=2),
        model_definition=ModelDefinition(
            model_name="openai:gpt-5.1-mini",
            temperature=1.0,
            top_p=1.0,
            max_tokens=512,
            timeout_seconds=60.0,
        ),
        model_alias="gpt-5.1-mini",
    )


def test_create_agent_returns_project_agent_with_protocol_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = PydanticAgentAIFactory()
    base_tool = _FakeTool(name="base", ctx=None)
    toolset_tool = _FakeTool(name="toolset-tool", ctx=object())
    config = _build_configuration(
        tools=[cast(Tool, base_tool)],
        toolsets=[cast(Toolset, _FakeToolset(tools=[toolset_tool]))],
        deps=_DependencyContainer(tenant_id="tenant-1"),
    )

    monkeypatch.setattr(
        factory_module,
        "resolve_ai_model_config",
        lambda _: _build_resolved_model_config(),
    )

    captured_construct_arguments: dict[str, object] = {}

    def _fake_construct_pydantic_agent(**kwargs: object) -> object:
        captured_construct_arguments.update(kwargs)
        return SimpleNamespace(run=None, run_stream=None)

    monkeypatch.setattr(
        factory, "_construct_pydantic_agent", _fake_construct_pydantic_agent
    )

    result = factory.create_agent(config)

    assert isinstance(result, ProjectPydanticAgent)
    assert result.output_type is str
    assert result.dependencies_type is _DependencyContainer
    assert result.tools == config.tools
    assert result.toolsets == config.toolsets
    assert result.history_tracker is factory.history_processor

    assert captured_construct_arguments["model_name"] == "openai:gpt-5.1-mini"
    mapped_tools = cast(list[object], captured_construct_arguments["tools"])
    assert len(mapped_tools) == 2
    assert (
        captured_construct_arguments["history_processor"] is factory.history_processor
    )


def test_map_tools_sets_takes_ctx_flag_from_tool_ctx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = PydanticAgentAIFactory()
    without_context = _FakeTool(name="without-context", ctx=None)
    with_context = _FakeTool(name="with-context", ctx={"scope": "internal"})
    captured_calls: list[dict[str, object]] = []

    def _fake_from_schema(*args: object, **kwargs: object) -> dict[str, object]:
        del args
        captured_calls.append(dict(kwargs))
        return dict(kwargs)

    monkeypatch.setattr(factory_module.PydanticTool, "from_schema", _fake_from_schema)

    mapped_tools = factory._map_tools_to_pydantic_tools(
        [cast(Tool, without_context), cast(Tool, with_context)]
    )

    assert len(mapped_tools) == 2
    assert captured_calls[0]["takes_ctx"] is False
    assert captured_calls[1]["takes_ctx"] is True
    assert captured_calls[0]["name"] == "without-context"
    assert captured_calls[1]["name"] == "with-context"


def test_map_model_settings_includes_optional_fields_when_set() -> None:
    factory = PydanticAgentAIFactory()
    model_settings = ModelSettings(
        temperature=0.7,
        top_p=0.8,
        max_tokens=256,
        timeout_seconds=20.0,
        stop_sequences=["END"],
        presence_penalty=0.3,
        frequency_penalty=0.2,
        seed=42,
        logit_bias={"12": -1},
        parallel_tool_calls=True,
        extra_headers={"X-Test": "yes"},
        extra_body={"safe": True},
    )

    mapped_settings = factory._map_model_settings(model_settings)

    assert mapped_settings.get("presence_penalty") == 0.3
    assert mapped_settings.get("frequency_penalty") == 0.2
    assert mapped_settings.get("seed") == 42


def test_map_model_settings_uses_copies_for_collections() -> None:
    factory = PydanticAgentAIFactory()
    model_settings = ModelSettings(
        temperature=1.0,
        top_p=1.0,
        max_tokens=512,
        timeout_seconds=60.0,
        stop_sequences=["HALT"],
        logit_bias={"1": 10},
        extra_headers={"Authorization": "masked"},
    )

    mapped_settings = factory._map_model_settings(model_settings)

    model_settings.stop_sequences.append("STOP")
    model_settings.logit_bias["2"] = 20
    model_settings.extra_headers["X-New"] = "1"

    assert mapped_settings.get("stop_sequences") == ["HALT"]
    assert mapped_settings.get("logit_bias") == {"1": 10}
    assert mapped_settings.get("extra_headers") == {"Authorization": "masked"}


def test_resolve_dependencies_type_returns_none_type_for_missing_deps() -> None:
    factory = PydanticAgentAIFactory()

    resolved_type = factory._resolve_dependencies_type(None)

    assert resolved_type is type(None)


def test_resolve_dependencies_type_returns_runtime_type_for_present_deps() -> None:
    factory = PydanticAgentAIFactory()
    deps = _DependencyContainer(tenant_id="tenant-2")

    resolved_type = factory._resolve_dependencies_type(deps)

    assert resolved_type is _DependencyContainer


def test_construct_pydantic_agent_passes_history_processor_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = PydanticAgentAIFactory()
    config = _build_configuration(deps=_DependencyContainer(tenant_id="tenant-3"))
    captured_constructor_kwargs: dict[str, object] = {}

    def _fake_pydantic_agent(**kwargs: object) -> dict[str, object]:
        captured_constructor_kwargs.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(factory_module, "PydanticAgent", _fake_pydantic_agent)

    created_agent = factory._construct_pydantic_agent(
        config=config,
        provider_name="openai",
        model_name="openai:gpt-5.1-mini",
        tools=[],
        dependencies_type=_DependencyContainer,
        history_processor=factory.history_processor,
    )

    assert created_agent == {"status": "ok"}
    assert captured_constructor_kwargs["history_processors"] == [
        factory.history_processor
    ]
    assert captured_constructor_kwargs["tool_timeout"] == 15.0


async def test_factory_built_agent_can_run_with_dependencies_and_mocked_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = PydanticAgentAIFactory()
    dependency_container = _DependencyContainer(tenant_id="tenant-4")
    config = _build_configuration(deps=dependency_container)

    monkeypatch.setattr(
        factory_module,
        "resolve_ai_model_config",
        lambda _: _build_resolved_model_config(),
    )

    run_stream_events_mock = MagicMock(
        return_value=_ResultEventsIterator(output="mocked-output")
    )
    mocked_pydantic_agent = SimpleNamespace(
        run_stream_events=run_stream_events_mock,
        run_stream=None,
    )

    monkeypatch.setattr(
        factory,
        "_construct_pydantic_agent",
        lambda **_: mocked_pydantic_agent,
    )

    built_agent = cast(
        ProjectPydanticAgent[str, _DependencyContainer], factory.create_agent(config)
    )
    built_agent.add_dependency(dependency_container)

    result = await built_agent.run("execute")

    assert result == "mocked-output"
    run_stream_events_mock.assert_called_once_with("execute", deps=dependency_container)


async def test_factory_built_agent_runs_tool_when_mocked_model_requests_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = PydanticAgentAIFactory()
    dependency_container = _DependencyContainer(tenant_id="tenant-tools")
    recording_tool = _RecordingTool(name="echo_tool", ctx=None)
    config = _build_configuration(
        deps=dependency_container,
        tools=[cast(Tool, recording_tool)],
    )

    monkeypatch.setattr(
        factory_module,
        "resolve_ai_model_config",
        lambda _: _build_resolved_model_config(),
    )

    def _fake_from_schema(*args: object, **kwargs: object) -> dict[str, object]:
        del args
        return dict(kwargs)

    monkeypatch.setattr(factory_module.PydanticTool, "from_schema", _fake_from_schema)

    captured_run_events_mock: dict[str, MagicMock] = {}

    def _fake_construct_pydantic_agent(**kwargs: object) -> object:
        mapped_tools = cast(list[dict[str, object]], kwargs["tools"])

        def _mocked_model_run_events(
            prompt: str, deps: _DependencyContainer
        ) -> _ResultEventsIterator:
            del prompt
            requested_tool_name = "echo_tool"
            selected_tool = next(
                mapped_tool
                for mapped_tool in mapped_tools
                if mapped_tool["name"] == requested_tool_name
            )
            selected_function = cast(
                Callable[..., str],
                selected_tool["function"],
            )
            tool_result = selected_function(text="from-model")
            return _ResultEventsIterator(
                output=f"{tool_result}|tenant={deps.tenant_id}"
            )

        run_stream_events_mock = MagicMock(side_effect=_mocked_model_run_events)
        captured_run_events_mock["run_stream_events"] = run_stream_events_mock
        return SimpleNamespace(
            run_stream_events=run_stream_events_mock, run_stream=None
        )

    monkeypatch.setattr(
        factory, "_construct_pydantic_agent", _fake_construct_pydantic_agent
    )

    built_agent = cast(
        ProjectPydanticAgent[str, _DependencyContainer],
        factory.create_agent(config),
    )
    built_agent.add_dependency(dependency_container)

    result = await built_agent.run("please use your tool")

    assert result == "tool-echo:from-model|tenant=tenant-tools"
    assert recording_tool.calls == ["from-model"]
    captured_run_events_mock["run_stream_events"].assert_called_once_with(
        "please use your tool",
        deps=dependency_container,
    )
