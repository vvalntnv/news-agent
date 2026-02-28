from typing import AsyncIterable

from pydantic import BaseModel

from domain.ai.configuration import AIConfiguration
from domain.ai.protocols import DependenciesType, Tool, Toolset, Agent as AgentProtocol
from pydantic_ai import Agent


# Here D is the depencency type and T is the return type of the model
class PydanticAgent[T: type, D](AgentProtocol):
    def __init__(
        self,
        # TODO: Is this the best method?
        agent: Agent[D | None, T],
        *,
        output_model: BaseModel,
        config: AIConfiguration,
        dependencies: DependenciesType,
    ) -> None:
        self.config = config
        self.tools = []
        self.toolsets = []
        self.agent = agent
        self.output_model = output_model
        self.dependencies = dependencies

    async def stream(
        self,
        prompt: str,
    ) -> AsyncIterable[str]:
        async with self.agent.run_stream(prompt) as stream_handle:
            return stream_handle.stream_text()

    async def stream_text(self, prompt: str) -> AsyncIterable[str]:
        raise NotImplementedError()

    async def respond(
        self,
        prompt: str,
    ) -> T:
        if self.agent.output_type is not str:
            raise Exception

        # Here maybe we do something with the result that we obtain?
        result = await self.agent.run(prompt)

        return result.output
