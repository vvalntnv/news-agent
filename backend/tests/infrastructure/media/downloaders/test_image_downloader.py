from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator, cast

import httpx
import pytest

from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink
from infrastructure.media.downloaders.image_downloader import ImageDownloader

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
        del method
        try:
            status_code, chunks = self._responses[url].pop(0)
        except KeyError as exc:
            raise RuntimeError("unexpected URL") from exc
        return _FakeStream(url, status_code, chunks)

    async def aclose(self) -> None:  # pragma: no cover - no resources
        return None


async def test_image_downloader_uses_shared_download_flow(tmp_path: Path) -> None:
    links = [
        MediaDownloadableLink(url="https://example.com/cover.jpg", sequence_number=0),
        MediaDownloadableLink(url="https://example.com/detail.jpg", sequence_number=1),
    ]
    responses = {
        "https://example.com/cover.jpg": [(200, [b"cover"])],
        "https://example.com/detail.jpg": [(200, [b"detail"])],
    }

    downloader = ImageDownloader(
        path_to_download=tmp_path,
        image_urls=links,
        source_url="https://example.com/gallery",
        stream_type=SupportedStreamTypes.DIRECT,
        client=cast(httpx.AsyncClient, _FakeClient(responses)),
    )

    downloaded = await downloader.download_image()

    assert downloaded.stream_type == SupportedStreamTypes.DIRECT
    assert [chunk.source_url for chunk in downloaded.chunks] == [
        "https://example.com/cover.jpg",
        "https://example.com/detail.jpg",
    ]
    assert downloaded.chunks[0].file_path.read_bytes() == b"cover"
    assert downloaded.chunks[1].file_path.read_bytes() == b"detail"


async def test_image_downloader_cleans_up_on_failure(tmp_path: Path) -> None:
    responses = {"https://example.com/fail.jpg": [(500, [])]}
    downloader = ImageDownloader(
        path_to_download=tmp_path,
        image_urls=[
            MediaDownloadableLink(
                url="https://example.com/fail.jpg",
                sequence_number=1,
            )
        ],
        source_url="https://example.com/gallery",
        client=cast(httpx.AsyncClient, _FakeClient(responses)),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await downloader.download_image()

    assert not tmp_path.exists()
