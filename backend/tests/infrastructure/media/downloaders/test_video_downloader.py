import pytest
import httpx

from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink
from infrastructure.media.downloaders.video_downloader import VideoDownloader

pytestmark = pytest.mark.anyio


def _build_client(payloads: dict[str, bytes]) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = payloads.get(str(request.url))
        if payload is None:
            return httpx.Response(status_code=404)

        return httpx.Response(status_code=200, content=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_video_downloader_downloads_segments_in_order(tmp_path) -> None:
    urls = [
        MediaDownloadableLink(
            url="https://example.com/chunk-11.ts",
            sequence_number=11,
            is_initialization_segment=False,
        ),
        MediaDownloadableLink(
            url="https://example.com/init.mp4",
            sequence_number=10,
            is_initialization_segment=True,
        ),
        MediaDownloadableLink(
            url="https://example.com/chunk-10.ts",
            sequence_number=10,
            is_initialization_segment=False,
        ),
    ]
    client = _build_client(
        {
            "https://example.com/init.mp4": b"init",
            "https://example.com/chunk-10.ts": b"chunk-10",
            "https://example.com/chunk-11.ts": b"chunk-11",
        }
    )

    downloader = VideoDownloader(
        path_to_download=tmp_path,
        chunks_data=urls,
        stream_type=SupportedStreamTypes.HLS,
        source_url="https://example.com/master.m3u8",
        client=client,
    )

    downloaded_media = await downloader.download_video()

    assert downloaded_media.stream_type == SupportedStreamTypes.HLS
    assert len(downloaded_media.chunks) == 3
    assert downloaded_media.chunks[0].is_initialization_segment is True
    assert downloaded_media.chunks[0].file_path.read_bytes() == b"init"
    assert downloaded_media.chunks[1].file_path.read_bytes() == b"chunk-10"
    assert downloaded_media.chunks[2].file_path.read_bytes() == b"chunk-11"
    await client.aclose()


async def test_video_downloader_skips_sort_when_links_already_sorted(
    tmp_path, monkeypatch
) -> None:
    urls = [
        MediaDownloadableLink(
            url="https://example.com/init.mp4",
            sequence_number=10,
            is_initialization_segment=True,
        ),
        MediaDownloadableLink(
            url="https://example.com/chunk-10.ts",
            sequence_number=10,
            is_initialization_segment=False,
        ),
        MediaDownloadableLink(
            url="https://example.com/chunk-11.ts",
            sequence_number=11,
            is_initialization_segment=False,
        ),
    ]

    client = _build_client({})
    downloader = VideoDownloader(
        path_to_download=tmp_path,
        chunks_data=urls,
        stream_type=SupportedStreamTypes.HLS,
        source_url="https://example.com/master.m3u8",
        client=client,
    )

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("sorted() should not be called for already ordered links")

    monkeypatch.setattr("builtins.sorted", _raise_if_called)

    ordered = downloader._prepare_ordered_urls()

    assert ordered is urls
    await client.aclose()
