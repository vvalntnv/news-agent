from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from application.background_jobs.payloads import MediaDownloadJobPayload
from infrastructure.background_jobs.tasks import media_download as task_module


def test_download_media_task_validates_payload_json() -> None:
    with pytest.raises(ValidationError):
        task_module.download_media_task('{"source_urls":[]}')


def test_download_media_task_delegates_to_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = MediaDownloadJobPayload(source_urls=["https://example.com/video.mp4"])
    payload_json = payload.model_dump_json()
    service_mock = AsyncMock()

    class _ServiceStub:
        def __init__(self) -> None:
            self.download_media = service_mock

    monkeypatch.setattr(task_module, "MediaDownloadService", _ServiceStub)

    task_module.download_media_task(payload_json)

    service_mock.assert_awaited_once()
    called_payload = service_mock.await_args_list[0].args[0]
    assert isinstance(called_payload, MediaDownloadJobPayload)
    assert called_payload.source_urls == ["https://example.com/video.mp4"]
