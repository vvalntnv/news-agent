from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest

from application.background_jobs.payloads import MediaDownloadJobPayload
from infrastructure.background_jobs.celery_app import celery_app
from infrastructure.background_jobs.celery_enqueuer import CeleryBackgroundJobEnqueuer
from infrastructure.background_jobs.tasks import media_download as task_module


class _EnqueueResultStub:
    def __init__(self, task_id: str | None) -> None:
        self.id = task_id


@pytest.fixture
def eager_mode_celery_config(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Temporarily enable eager mode for Celery tasks with proper cleanup."""
    previous_task_always_eager = celery_app.conf.task_always_eager
    previous_task_eager_propagates = celery_app.conf.task_eager_propagates

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    yield

    celery_app.conf.task_always_eager = previous_task_always_eager
    celery_app.conf.task_eager_propagates = previous_task_eager_propagates


def test_enqueue_job_serializes_pydantic_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueuer = CeleryBackgroundJobEnqueuer()
    payload = MediaDownloadJobPayload(source_urls=["https://example.com/video.mp4"])
    media_download_job = celery_app.tasks["background_jobs.media_download"]
    captured: dict[str, object] = {}

    def _fake_apply_async(*, args: list[object], serializer: str) -> _EnqueueResultStub:
        captured["args"] = args
        captured["serializer"] = serializer
        return _EnqueueResultStub(task_id="task-123")

    monkeypatch.setattr(media_download_job, "apply_async", _fake_apply_async)

    result = enqueuer.enqueue_job(media_download_job, payload)

    assert result.task_id == "task-123"
    assert captured["serializer"] == "json"
    assert captured["args"] == [payload.model_dump_json()]


def test_enqueue_job_raises_when_task_id_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueuer = CeleryBackgroundJobEnqueuer()
    media_download_job = celery_app.tasks["background_jobs.media_download"]

    def _fake_apply_async(*, args: list[object], serializer: str) -> _EnqueueResultStub:
        return _EnqueueResultStub(task_id=None)

    monkeypatch.setattr(media_download_job, "apply_async", _fake_apply_async)

    with pytest.raises(RuntimeError, match="empty task id"):
        enqueuer.enqueue_job(media_download_job, payload="raw-payload")


def test_enqueuer_runs_media_job_in_eager_mode(
    monkeypatch: pytest.MonkeyPatch,
    eager_mode_celery_config: None,
) -> None:
    service_mock = AsyncMock()

    class _ServiceStub:
        def __init__(self) -> None:
            self.download_media = service_mock

    monkeypatch.setattr(task_module, "MediaDownloadService", _ServiceStub)

    payload = MediaDownloadJobPayload(
        source_urls=["https://example.com/eager.mp4"],
    )

    enqueuer = CeleryBackgroundJobEnqueuer()
    result = enqueuer.enqueue_media_download_job(payload)

    assert len(result.task_id) > 0
    service_mock.assert_awaited_once()
