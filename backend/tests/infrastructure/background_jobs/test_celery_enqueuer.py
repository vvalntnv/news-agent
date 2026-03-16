from unittest.mock import AsyncMock

import pytest

from application.background_jobs.payloads import MediaDownloadJobPayload
from infrastructure.background_jobs.celery_app import celery_app
from infrastructure.background_jobs.celery_enqueuer import CeleryBackgroundJobEnqueuer
from infrastructure.background_jobs.tasks import media_download as task_module


def test_enqueuer_runs_media_job_in_eager_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_mock = AsyncMock()

    class _ServiceStub:
        def __init__(self) -> None:
            self.download_media = service_mock

    monkeypatch.setattr(task_module, "MediaDownloadService", _ServiceStub)

    previous_task_always_eager = celery_app.conf.task_always_eager
    previous_task_eager_propagates = celery_app.conf.task_eager_propagates

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    try:
        payload = MediaDownloadJobPayload(
            source_urls=["https://example.com/eager.mp4"],
        )

        enqueuer = CeleryBackgroundJobEnqueuer()
        result = enqueuer.enqueue_media_download_job(payload)

        assert len(result.task_id) > 0
        service_mock.assert_awaited_once()
    finally:
        celery_app.conf.task_always_eager = previous_task_always_eager
        celery_app.conf.task_eager_propagates = previous_task_eager_propagates
