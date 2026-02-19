from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import AsyncIterator, cast

import httpx
import pytest

from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink
from infrastructure.media.resolvers.dash_mpd_resolver import DashMPDResolver
from infrastructure.media.downloaders.video_downloader import VideoDownloader

pytestmark = pytest.mark.anyio


class _FakeStream:
    def __init__(self, url: str, status_code: int, chunks: list[bytes]) -> None:
        self._status_code = status_code
        self._chunks = chunks
        self.request = httpx.Request("GET", url)
        self.response = httpx.Response(status_code=status_code, request=self.request)

    async def __aenter__(self) -> _FakeStream:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        return None

    def raise_for_status(self) -> None:
        if self._status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=self.response,
            )

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


class _FakeClient:
    def __init__(self, responses: dict[str, list[tuple[int, list[bytes]]]]) -> None:
        self._responses = {url: list(sequence) for url, sequence in responses.items()}

    def stream(self, method: str, url: str) -> _FakeStream:
        try:
            status_code, chunks = self._responses[url].pop(0)
        except KeyError as exc:
            raise RuntimeError("unexpected URL") from exc
        return _FakeStream(url, status_code, chunks)

    async def aclose(self) -> None:  # pragma: no cover - no resources
        return None


async def test_video_downloader_retries_and_preserves_order(tmp_path: Path) -> None:
    chunk_links = [
        MediaDownloadableLink(url="https://example.com/2.ts", sequence_number=2),
        MediaDownloadableLink(url="https://example.com/1.ts", sequence_number=1),
    ]

    responses = {
        "https://example.com/1.ts": [
            (429, []),
            (200, [b"first"]),
        ],
        "https://example.com/2.ts": [(200, [b"second"])],
    }

    client = _FakeClient(responses)
    downloader = VideoDownloader(
        path_to_download=tmp_path,
        chunks_data=chunk_links,
        stream_type=SupportedStreamTypes.DIRECT,
        source_url="https://example.com/video",
        client=cast(httpx.AsyncClient, client),
    )

    media = await downloader.download_video()

    assert [chunk.source_url for chunk in media.chunks] == [
        "https://example.com/1.ts",
        "https://example.com/2.ts",
    ]
    assert media.chunks[0].file_path.read_bytes() == b"first"
    assert media.chunks[1].file_path.read_bytes() == b"second"


async def test_video_downloader_cleans_up_on_failure(tmp_path: Path) -> None:
    link = MediaDownloadableLink(url="https://example.com/fail.ts", sequence_number=1)
    responses = {"https://example.com/fail.ts": [(500, [])]}
    client = _FakeClient(responses)

    downloader = VideoDownloader(
        path_to_download=tmp_path,
        chunks_data=[link],
        stream_type=SupportedStreamTypes.DIRECT,
        source_url="https://example.com/fail",
        client=cast(httpx.AsyncClient, client),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await downloader.download_video()

    assert not tmp_path.exists()


# @pytest.mark.skip()
async def test_downloading_real_world_video() -> None:
    video_url = "https://edge125.vbox7.com/sl/iyl2RXibn5lNWR64cs6J9w/1771711200/92/9296ba3367/9296ba3367.mpd"
    with TemporaryDirectory() as tmp_dir:
        resolved_stream = await DashMPDResolver().resolve_stream(video_url)
        downloader = VideoDownloader(
            path_to_download=tmp_dir,
            chunks_data=resolved_stream.links,
            stream_type=SupportedStreamTypes.DASH,
            source_url=resolved_stream.source_url,
        )

        downloaded_media = await downloader.download_video()

        assert len(downloaded_media.chunks) > 0
        assert downloaded_media.chunks[0].file_path.exists()
