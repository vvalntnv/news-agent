from pydantic import BaseModel
from domain.ai.protocols import Agent
from application.ai.workflow.step import WorkflowStep


class Test(BaseModel): ...


class Workflow[O: BaseModel]:
    def __init__[D](self, step_graph_entry: WorkflowStep, agent: Agent[O, D]) -> None:
        self.entrypoint = step_graph_entry
        self.agent = agent

    def execute_workflow(self) -> O:
        results = []
        while current_step := self.entrypoint.get_next():
            if not current_step.has_agent_assigned:
                current_step.set_agent(self.agent)

            result = current_step.execute()
            results.append(result)

        return results[-1]
