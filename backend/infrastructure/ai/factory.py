from domain.ai.configuration import AIConfiguration
from domain.ai.protocols import Agent
from domain.ai.factory import AIFactory


class PydanticAIFactory(AIFactory):
    def __init__(self, config) -> None:
        super().__init__()

    def create_agent(self, config: AIConfiguration) -> Agent:
        return super().create_agent(config)
