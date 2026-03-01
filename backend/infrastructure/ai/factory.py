from typing import cast

from pydantic import BaseModel

from pydantic_ai import Agent as PydanticAgent, Tool as PydanticTool
from pydantic_ai.settings import ModelSettings as PydanticModelSettings

from domain.ai.configuration import AIConfiguration, ModelSettings
from domain.ai.protocols import AIFactory, Agent, Tool, Toolset
from core.utils.ai_models import resolve_ai_model_config
from infrastructure.ai.agent import ProjectPydanticAgent


class PydanticAgentAIFactory(AIFactory):
    def __init__(self) -> None:
        super().__init__()

    def create_agent[O: (BaseModel, str), D](
        self, config: AIConfiguration[O, D]
    ) -> Agent[O, D]:
        model_config = resolve_ai_model_config(config)
        tools = self._map_tools_to_pydantic_tools(config.tools)
        tools.extend(self._map_toolsets_to_pydantic_tools(config.toolsets))
        dependencies_type = self._resolve_dependencies_type(config.deps)

        pydantic_agent = self._construct_pydantic_agent(
            config=config,
            model_name=model_config.model_definition.model_name,
            tools=tools,
            dependencies_type=dependencies_type,
        )

        return cast(
            Agent[O, D],
            ProjectPydanticAgent(
                agent=pydantic_agent,
                output_type=config.output_type,
                dependencies_type=dependencies_type,
                tools=config.tools,
                toolsets=config.toolsets,
            ),
        )

    def _construct_pydantic_agent[O: (BaseModel, str), D](
        self,
        config: AIConfiguration[O, D],
        model_name: str,
        tools: list[PydanticTool],
        dependencies_type: type[D],
    ) -> PydanticAgent[D, O]:
        mapped_model_settings = self._map_model_settings(config.model_settings)

        return PydanticAgent(
            model=model_name,
            output_type=config.output_type,
            instructions=config.instructions,
            system_prompt=tuple(config.system_prompt),
            deps_type=dependencies_type,
            name=config.agent_name,
            model_settings=mapped_model_settings,
            retries=config.retries,
            output_retries=config.output_retries,
            tools=tools,
            end_strategy=config.end_strategy,
            metadata=dict(config.metadata),
            tool_timeout=config.tool_timeout_seconds,
        )

    def _map_model_settings(
        self, model_settings: ModelSettings
    ) -> PydanticModelSettings:
        mapped_model_settings: dict[str, object] = {
            "temperature": model_settings.temperature,
            "top_p": model_settings.top_p,
            "max_tokens": model_settings.max_tokens,
            "timeout": model_settings.timeout_seconds,
            "stop_sequences": list(model_settings.stop_sequences),
            "logit_bias": dict(model_settings.logit_bias),
            "parallel_tool_calls": model_settings.parallel_tool_calls,
            "extra_headers": dict(model_settings.extra_headers),
            "extra_body": model_settings.extra_body,
        }

        if model_settings.presence_penalty is not None:
            mapped_model_settings["presence_penalty"] = model_settings.presence_penalty

        if model_settings.frequency_penalty is not None:
            mapped_model_settings["frequency_penalty"] = (
                model_settings.frequency_penalty
            )

        if model_settings.seed is not None:
            mapped_model_settings["seed"] = model_settings.seed

        return cast(PydanticModelSettings, mapped_model_settings)

    def _resolve_dependencies_type[D](self, dependencies: D | None) -> type[D]:
        if dependencies is None:
            return cast(type[D], type(None))

        return type(dependencies)

    def _map_tools_to_pydantic_tools(self, tools: list[Tool]) -> list[PydanticTool]:
        mapped_tools: list[PydanticTool] = []
        for tool in tools:
            takes_ctx = tool.ctx is not None
            mapped_tools.append(
                PydanticTool.from_schema(
                    function=tool.__call__,
                    name=tool.name,
                    description=tool.description,
                    json_schema=dict(tool.json_schema),
                    takes_ctx=takes_ctx,
                )
            )
        return mapped_tools

    def _map_toolsets_to_pydantic_tools(
        self, toolsets: list[Toolset]
    ) -> list[PydanticTool]:
        mapped_tools: list[PydanticTool] = []
        for toolset in toolsets:
            mapped_tools.extend(self._map_tools_to_pydantic_tools(toolset.tools))
        return mapped_tools
