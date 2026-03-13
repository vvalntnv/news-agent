from pydantic import BaseModel

from application.ai.workflow.step import WorkflowStep
from domain.ai.protocols import Agent


class Workflow[S: BaseModel, O: (BaseModel, str), D]:
    def __init__(
        self,
        step_graph_entry: WorkflowStep[S, O, D],
        agent: Agent[O, D],
    ) -> None:
        self.entrypoint: WorkflowStep[S, O, D]
        self.agent: Agent[O, D]
        self.entrypoint = step_graph_entry
        self.agent = agent

    async def execute_workflow(self) -> O:
        final_result: O | None = None
        current_step: WorkflowStep[S, O, D] | None = self.entrypoint

        while current_step is not None:
            if not current_step.has_agent_assigned:
                current_step.set_agent(self.agent)

            result = await current_step.execute()
            # TODO: maybe here we want to somehow check if a transition condition has happened, because what if it does not?
            final_result = result
            current_step = current_step.get_next()

        if final_result is None:
            raise Exception("Workflow did not execute any steps")

        return final_result
