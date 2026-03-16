from pathlib import Path

import pytest

from application.background_jobs.payloads import MediaDownloadJobPayload
from application.services.media_download_service import MediaDownloadService
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MuxedMedia

pytestmark = pytest.mark.anyio


class _MediaDownloadHandlerStub:
    async def download_media(self, source_urls: list[str]) -> list[MuxedMedia]:
        return [
            MuxedMedia(
                source_url=source_urls[0],
                stream_type=SupportedStreamTypes.DIRECT,
                output_path=Path("/tmp/video.mp4"),
                static_url_path="/static/media/video.mp4",
            )
        ]


async def test_media_download_service_maps_muxed_output() -> None:
    payload = MediaDownloadJobPayload(
        source_urls=["https://example.com/video.mp4"],
    )
    service = MediaDownloadService(
        media_download_handler=_MediaDownloadHandlerStub(),
    )

    result = await service.download_media(payload)

    assert len(result.outputs) == 1
    assert result.outputs[0].source_url == "https://example.com/video.mp4"
    assert result.outputs[0].stream_type == SupportedStreamTypes.DIRECT
    assert result.outputs[0].output_path == "/tmp/video.mp4"
    assert result.outputs[0].static_url_path == "/static/media/video.mp4"
