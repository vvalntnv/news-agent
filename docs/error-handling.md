# Error Handling

This project uses two custom error types with a shared JSON payload model. The
goal is to make client-facing errors explicit and keep internal errors logged
server-side only.

## Error Payload

Errors are represented by `ErrorPayload` in `backend/core/errors/base.py`:

- `code`: stable, machine-readable error code
- `message`: human-readable summary
- `details`: optional dictionary of string keys and values

## Client Errors

Use `ClientError` for errors that should be returned to the client. It carries
an `ErrorPayload` and a configurable HTTP status code.

Example (raised in a route handler):

```python
raise ClientError(
    payload=ErrorPayload(
        code="bad_request",
        message="Invalid request",
        details={"field": "title"},
    ),
    status_code=422,
)
```

## Internal Errors

Use `InternalError` for errors that should be logged and returned as a generic
500 response. It contains:

- `internal_payload`: full internal details for logging
- `public_payload`: sanitized payload returned to clients

If no `public_payload` is provided, the default is:

```json
{"code": "internal_error", "message": "Internal server error", "details": null}
```

## FastAPI Handlers

Register error handlers with:

```python
from application.error_handlers import register_error_handlers

register_error_handlers(app)
```

The handler:

- Returns `ClientError.payload` and its status code to the client
- Logs `InternalError.internal_payload` and returns `public_payload` with HTTP 500

## Web Scraper Missing Title

`MissingTitleError` is raised when a scraped link does not produce a valid title.
`WebScraperSource` catches this error and skips the item, preventing invalid
articles from entering the pipeline.
