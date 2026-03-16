from pydantic import BaseModel


class WorkflowState(BaseModel):
    last_validation_error: str | None = None
