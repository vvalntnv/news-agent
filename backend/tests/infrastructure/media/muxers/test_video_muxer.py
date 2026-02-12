import os
from pathlib import Path

import pytest

from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, DownloadedMediaChunk
from infrastructure.media.muxers.video_muxer import VideoMuxer

pytestmark = pytest.mark.anyio


class _ProcessStub:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""


async def test_video_muxer_uses_half_cpu_cores_and_returns_static_path(
    tmp_path, monkeypatch
) -> None:
    input_chunk = tmp_path / "input.mp4"
    input_chunk.write_bytes(b"video-data")

    downloaded_media = DownloadedMedia(
        source_url="https://example.com/video.mp4",
        stream_type=SupportedStreamTypes.DIRECT,
        chunks=[
            DownloadedMediaChunk(
                source_url="https://example.com/video.mp4",
                file_path=input_chunk,
                sequence_number=1,
                is_initialization_segment=False,
            )
        ],
    )

    captured_args: list[str] = []

    async def fake_subprocess_exec(*args: str, **_kwargs: object) -> _ProcessStub:
        captured_args.extend(list(args))
        Path(args[-1]).write_bytes(b"muxed")
        return _ProcessStub()

    monkeypatch.setattr(
        "infrastructure.media.muxers.video_muxer.asyncio.create_subprocess_exec",
        fake_subprocess_exec,
    )

    muxer = VideoMuxer(static_media_root=tmp_path / "static" / "media")
    muxed_media = await muxer.mux(downloaded_media, output_file_name="result")

    expected_threads = max(1, (os.cpu_count() or 1) // 2)
    threads_index = captured_args.index("-threads")

    assert captured_args[threads_index + 1] == str(expected_threads)
    assert muxed_media.output_path.exists()
    assert muxed_media.static_url_path == "/static/media/result.mp4"


async def test_video_muxer_uses_concat_for_multiple_chunks(
    tmp_path, monkeypatch
) -> None:
    chunk_a = tmp_path / "chunk-1.ts"
    chunk_b = tmp_path / "chunk-2.ts"
    chunk_a.write_bytes(b"a")
    chunk_b.write_bytes(b"b")

    downloaded_media = DownloadedMedia(
        source_url="https://example.com/master.m3u8",
        stream_type=SupportedStreamTypes.HLS,
        chunks=[
            DownloadedMediaChunk(
                source_url="https://example.com/chunk-1.ts",
                file_path=chunk_a,
                sequence_number=1,
                is_initialization_segment=False,
            ),
            DownloadedMediaChunk(
                source_url="https://example.com/chunk-2.ts",
                file_path=chunk_b,
                sequence_number=2,
                is_initialization_segment=False,
            ),
        ],
    )

    captured_args: list[str] = []

    async def fake_subprocess_exec(*args: str, **_kwargs: object) -> _ProcessStub:
        captured_args.extend(list(args))
        Path(args[-1]).write_bytes(b"muxed")
        return _ProcessStub()

    monkeypatch.setattr(
        "infrastructure.media.muxers.video_muxer.asyncio.create_subprocess_exec",
        fake_subprocess_exec,
    )

    muxer = VideoMuxer(static_media_root=tmp_path / "static" / "media")
    await muxer.mux(downloaded_media, output_file_name="joined")

    assert "-f" in captured_args
    assert "concat" in captured_args
