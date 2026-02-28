from typing import AsyncIterable

from domain.ai.configuration import AIConfiguration
from domain.ai.protocols import Tool, Toolset, Agent as AgentProtocol
from pydantic_ai import Agent


class PydanticAgent(AgentProtocol):
    def __init__(
        self,
        agent: Agent,
        config: AIConfiguration,
        tools: list[Tool] = [],
        toolsets: list[Toolset] = [],
    ) -> None:
        self.config = config
        self.agent = agent

    async def stream(
        self,
        prompt: str,
    ) -> AsyncIterable[str]:
        async with self.agent.run_stream(prompt) as stream_handle:
            return stream_handle.stream_text()

    async def respond(
        self,
        prompt: str,
    ) -> str: ...
