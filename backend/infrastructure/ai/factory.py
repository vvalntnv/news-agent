from pydantic import BaseModel

from domain.ai.configuration import AIConfiguration
from domain.ai.protocols import AIFactory, Agent, DependenciesType, Tool
from core.utils.ai_models import resolve_ai_model_config
from pydantic_ai import Tool as PydanticTool, RunContext


class PydanticAgentAIFactory(AIFactory):
    def __init__(self) -> None:
        super().__init__()

    def create_agent[O: (BaseModel, str), D: DependenciesType](
        self, config: AIConfiguration[O, D]
    ) -> Agent[O, D]:
        model_config = resolve_ai_model_config(config)
        raise NotImplementedError("agent creation not wired yet")

    def _map_depencency_to_pydantic_run_context(
        self, dependencies: DependenciesType
    ) -> RunContext: ...

    def _map_tools_to_pydantic_tools(self, tools: list[Tool]) -> list[PydanticTool]: ...
