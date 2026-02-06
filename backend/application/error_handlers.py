import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.errors import ClientError, InternalError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClientError)
    async def handle_client_error(
        _request: Request, exc: ClientError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.payload.model_dump(),
        )

    @app.exception_handler(InternalError)
    async def handle_internal_error(
        _request: Request, exc: InternalError
    ) -> JSONResponse:
        internal_payload_json = json.dumps(exc.internal_payload.model_dump())
        logger.exception("Internal error: %s", internal_payload_json)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.public_payload.model_dump(),
        )
