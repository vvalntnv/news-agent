from core.errors.base import ErrorPayload, InternalError


class WorkflowDependencyNotConfiguredError(InternalError):
    def __init__(self, workflow_name: str, step_name: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="workflow_dependency_not_configured",
                message="Workflow agent dependency is not configured.",
                details={
                    "workflow_name": workflow_name,
                    "step_name": step_name,
                },
            )
        )


class WorkflowDependencyResolutionError(InternalError):
    def __init__(
        self,
        workflow_name: str,
        step_name: str,
        reason: str,
    ) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="workflow_dependency_resolution_error",
                message="Workflow dependency could not be resolved.",
                details={
                    "workflow_name": workflow_name,
                    "step_name": step_name,
                    "reason": reason,
                },
            )
        )


class WorkflowStepValidationFailedError(InternalError):
    def __init__(
        self,
        *,
        step_name: str,
        validator_name: str,
        attempt_number: int,
        reason: str,
    ) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="workflow_step_validation_failed",
                message="Workflow step validation failed.",
                details={
                    "step_name": step_name,
                    "validator_name": validator_name,
                    "attempt_number": str(attempt_number),
                    "reason": reason,
                },
            )
        )


class WorkflowStepRetryExhaustedError(InternalError):
    def __init__(
        self,
        *,
        step_name: str,
        max_retries: int,
        last_error_code: str,
        last_error_message: str,
    ) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="workflow_step_retry_exhausted",
                message="Workflow step retries were exhausted.",
                details={
                    "step_name": step_name,
                    "max_retries": str(max_retries),
                    "last_error_code": last_error_code,
                    "last_error_message": last_error_message,
                },
            )
        )


class WorkflowLoopLimitExceededError(InternalError):
    def __init__(self, workflow_name: str, max_steps: int, step_name: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="workflow_loop_limit_exceeded",
                message="Workflow execution exceeded the configured step limit.",
                details={
                    "workflow_name": workflow_name,
                    "max_steps": str(max_steps),
                    "step_name": step_name,
                },
            )
        )


class WorkflowNoResultError(InternalError):
    def __init__(self, workflow_name: str) -> None:
        super().__init__(
            internal_payload=ErrorPayload(
                code="workflow_no_result",
                message="Workflow completed without a final result.",
                details={
                    "workflow_name": workflow_name,
                },
            )
        )
