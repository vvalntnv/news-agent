from pydantic import BaseModel
import pydantic_ai
from domain.ai.configuration import AIConfiguration
from domain.ai.protocols import Agent
from domain.ai.factory import AIFactory
from core.config import config as global_conf, ModelDefinition


from infrastructure.ai.agent import PydanticAgent


class PydanticAIFactory(AIFactory):
    def __init__(self, config) -> None:
        super().__init__()

    def create_agent[O: BaseModel](self, config: AIConfiguration) -> Agent:
        assert global_conf.models is not None, "Configuration not properly set up"

        provider_name, model_name = self._get_model_name(config)

        model_conf = global_conf.models.get_model(
            provider_name=provider_name,
            model_alias=model_name,
        )

        if not model_conf:
            # ReviewComment:here i need a custom exception
            raise Exception("No model definition found here")

        agent = self._build_agent(model_conf, config)
        return agent

    def _build_agent[O: BaseModel](
        self,
        model_conf: ModelDefinition,
        config: AIConfiguration,
    ) -> Agent[O]:
        inner_actor = pydantic_ai.Agent()
        agent = PydanticAgent(
            agent=inner_actor,
            config=config,
            output_model=config.output_type,
            dependencies={},
        )

        return agent

    def _get_model_name(self, config: AIConfiguration) -> tuple[str, str]:
        model_name = config.model_name
        provider_name: str | None = config.provider_name

        provider_from_model: str | None = None
        model_alias = model_name

        if "/" in model_name:
            candidate_provider, candidate_model = model_name.split("/", maxsplit=1)
            provider_from_model = candidate_provider or None
            model_alias = candidate_model

        if provider_name is None:
            provider_name = provider_from_model

        if provider_name is None:
            raise Exception("unable to determine AI model provider")

        return provider_name, model_alias
