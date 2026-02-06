from __future__ import annotations

from pydantic import BaseModel


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, str] | None = None


class ClientError(Exception):
    def __init__(self, payload: ErrorPayload, status_code: int = 400) -> None:
        self.payload = payload
        self.status_code = status_code
        super().__init__(payload.message)


class InternalError(Exception):
    status_code: int = 500

    def __init__(
        self,
        internal_payload: ErrorPayload,
        public_payload: ErrorPayload | None = None,
    ) -> None:
        self.internal_payload = internal_payload
        self.public_payload = public_payload or ErrorPayload(
            code="internal_error",
            message="Internal server error",
        )
        super().__init__(internal_payload.message)
