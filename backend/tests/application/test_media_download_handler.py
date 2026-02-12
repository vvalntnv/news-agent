from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.endpoints.static_files import mount_static_files
from application.media_download_handler import MediaDownloadHandler
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import (
    DownloadedMedia,
    DownloadedMediaChunk,
    MediaDownloadableLink,
    MuxedMedia,
    ResolvedMediaStream,
)

pytestmark = pytest.mark.anyio


class _ResolverStub:
    def __init__(self) -> None:
        self.stream_type = SupportedStreamTypes.DIRECT

    async def can_resolve(self, stream_url: str) -> bool:
        return stream_url.endswith(".mp4")

    async def resolve_stream(self, video_to_resolve: str) -> ResolvedMediaStream:
        return ResolvedMediaStream(
            source_url=video_to_resolve,
            stream_type=SupportedStreamTypes.DIRECT,
            is_chunked=False,
            links=[
                MediaDownloadableLink(
                    url=video_to_resolve,
                    sequence_number=0,
                    is_initialization_segment=False,
                )
            ],
        )


class _DownloaderStub:
    def __init__(self, source_url: str, chunk_file: Path) -> None:
        self.path_to_download = chunk_file.parent
        self.video_urls: list[MediaDownloadableLink] = []
        self._source_url = source_url
        self._chunk_file = chunk_file

    async def download_video(self) -> DownloadedMedia:
        return DownloadedMedia(
            source_url=self._source_url,
            stream_type=SupportedStreamTypes.DIRECT,
            chunks=[
                DownloadedMediaChunk(
                    source_url=self._source_url,
                    file_path=self._chunk_file,
                    sequence_number=0,
                    is_initialization_segment=False,
                )
            ],
        )


class _MuxerStub:
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    async def mux(
        self,
        downloaded_media: DownloadedMedia,
        output_file_name: str | None = None,
    ) -> MuxedMedia:
        del output_file_name
        self._output_path.write_bytes(b"muxed")
        return MuxedMedia(
            source_url=downloaded_media.source_url,
            stream_type=downloaded_media.stream_type,
            output_path=self._output_path,
            static_url_path=f"/static/media/{self._output_path.name}",
        )


async def test_media_download_handler_orchestrates_pipeline(tmp_path) -> None:
    chunk_file = tmp_path / "downloaded.mp4"
    chunk_file.write_bytes(b"downloaded")

    output_file = tmp_path / "static" / "media" / "final.mp4"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    def downloader_factory(
        _path_to_download: Path,
        _chunks_data: list[MediaDownloadableLink],
        _stream_type: SupportedStreamTypes,
        source_url: str,
    ) -> _DownloaderStub:
        return _DownloaderStub(source_url=source_url, chunk_file=chunk_file)

    handler = MediaDownloadHandler(
        resolvers=[_ResolverStub()],
        muxer=_MuxerStub(output_path=output_file),
        download_root=tmp_path / "downloads",
        static_media_root=tmp_path / "static" / "media",
        downloader_factory=downloader_factory,
    )

    result = await handler.download_single("https://example.com/sample.mp4")

    assert result.output_path == output_file
    assert result.output_path.exists()
    assert result.static_url_path == "/static/media/final.mp4"


def test_mount_static_files_exposes_static_directory(tmp_path) -> None:
    app = FastAPI()
    static_root = tmp_path / "static"
    media_dir = static_root / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    sample_file = media_dir / "sample.txt"
    sample_file.write_text("hello", encoding="utf-8")

    mount_static_files(app, static_root=static_root)

    client = TestClient(app)
    response = client.get("/static/media/sample.txt")

    assert response.status_code == 200
    assert response.text == "hello"
