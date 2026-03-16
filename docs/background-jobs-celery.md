# Background Jobs with Celery

This document describes how Celery is integrated into the backend and how to
run jobs in either real worker mode or eager in-process mode for development.

## Goals

- Keep the domain layer Celery-free.
- Keep enqueue APIs strongly typed with Pydantic models.
- Use JSON serialization only (no pickle).
- Allow local development with eager tasks in the main process.

## Module Layout

- Celery app bootstrap: `backend/infrastructure/background_jobs/celery_app.py`
- Celery enqueue adapter: `backend/infrastructure/background_jobs/celery_enqueuer.py`
- Celery tasks: `backend/infrastructure/background_jobs/tasks/`
- Application payload models: `backend/application/background_jobs/payloads.py`
- Application enqueue protocol: `backend/application/background_jobs/protocols.py`
- Application service used by task: `backend/application/services/media_download_service.py`

## Configuration

All Celery behavior is configured in `backend/core/config.py` through
`Config.celery` (`CelerySettings`).

Key environment variables:

- `CELERY__BROKER_URL` (default: `redis://localhost:6379/0`)
- `CELERY__RESULT_BACKEND` (optional)
- `CELERY__TASK_ALWAYS_EAGER` (`true` runs tasks in-process)
- `CELERY__TASK_EAGER_PROPAGATES` (`true` re-raises task exceptions in eager mode)
- `CELERY__TASK_STORE_EAGER_RESULT` (optional eager result storage)
- `CELERY__TASK_IGNORE_RESULT` (default true)
- `CELERY__TASK_ACKS_LATE`
- `CELERY__WORKER_PREFETCH_MULTIPLIER`
- `CELERY__TASK_SOFT_TIME_LIMIT_SECONDS`
- `CELERY__TASK_TIME_LIMIT_SECONDS`
- `CELERY__IMPORTS` (tuple of task modules)

Serialization defaults are explicitly JSON:

- `task_serializer = "json"`
- `result_serializer = "json"`
- `event_serializer = "json"`
- `accept_content = ("json",)`
- `result_accept_content = ("json",)`

## Running

Run commands from `backend/`.

### Worker Mode (Redis)

1. Start Redis locally.
2. Start worker:

```bash
uv run celery -A infrastructure.background_jobs.celery_app:celery_app worker -l INFO
```

Optional scheduler process (when periodic tasks are added):

```bash
uv run celery -A infrastructure.background_jobs.celery_app:celery_app beat -l INFO
```

### Eager In-Process Mode (Development)

Set env variables before starting your app process:

```bash
export CELERY__TASK_ALWAYS_EAGER=true
export CELERY__TASK_EAGER_PROPAGATES=true
```

In this mode, `apply_async`/`delay` executes immediately in-process.

## Typed Boundaries

- Job payloads are Pydantic models.
- Enqueue converts payloads to JSON with `model_dump_json()`.
- Tasks deserialize with `model_validate_json()`.
- Task input stays `str` (`payload_json`) to keep transport format explicit.

## Current First Job

- Task: `background_jobs.media_download`
- Queue API: `CeleryBackgroundJobEnqueuer.enqueue_media_download_job(...)`
- Task implementation delegates to `MediaDownloadService` for business logic.

## Testing Strategy

- Unit test application orchestration with mocked enqueuers.
- Test task JSON validation and service delegation directly.
- Test eager behavior by enabling eager flags and calling enqueue methods.
- Add slow broker-backed tests separately when needed.
