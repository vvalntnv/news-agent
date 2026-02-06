import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.error_handlers import register_error_handlers
from core.errors import ClientError, ErrorPayload, InternalError


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/client-error")
    def client_error_route() -> dict[str, str]:
        raise ClientError(
            payload=ErrorPayload(
                code="bad_request",
                message="Invalid request",
                details={"field": "title"},
            ),
            status_code=422,
        )

    @app.get("/internal-error")
    def internal_error_route() -> dict[str, str]:
        raise InternalError(
            internal_payload=ErrorPayload(
                code="boom",
                message="Unexpected failure",
                details={"context": "test"},
            )
        )

    return app


def test_client_error_handler_returns_payload():
    app = _build_app()
    client = TestClient(app)

    response = client.get("/client-error")

    assert response.status_code == 422
    assert response.json() == {
        "code": "bad_request",
        "message": "Invalid request",
        "details": {"field": "title"},
    }


def test_internal_error_handler_logs_and_returns_generic_payload(caplog):
    app = _build_app()
    client = TestClient(app)

    caplog.set_level(logging.ERROR, logger="application.error_handlers")

    response = client.get("/internal-error")

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Internal server error",
        "details": None,
    }

    assert any('"code": "boom"' in record.message for record in caplog.records)
