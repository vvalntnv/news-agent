from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from core.config import config
from core.errors import MediaMuxNoChunksError
from domain.media.protocols import MediaMuxerProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, DownloadedMediaChunk, MuxedMedia
from infrastructure.media.muxers.ffmpeg.concatenate_dash_command import DASHFFMpegConcat
from infrastructure.media.muxers.ffmpeg.concatenate_hls_command import HLSFFMpegConcat
from infrastructure.media.muxers.ffmpeg.direct_file_compression_command import (
    DirectFileCompression,
)
from infrastructure.media.muxers.ffmpeg.ffmpeg_command import BaseFFMpegCommand


class VideoMuxer(MediaMuxerProtocol):
    def __init__(
        self,
        static_media_root: Path | str | None = None,
        ffmpeg_binary: str | None = None,
        ffmpeg_threads: int | None = None,
    ) -> None:
        self._static_media_root = Path(static_media_root or config.media_static_root)
        self._ffmpeg_binary = ffmpeg_binary or config.ffmpeg_binary
        self._configured_threads = ffmpeg_threads
        self._commands_by_stream_type: dict[
            SupportedStreamTypes, type[BaseFFMpegCommand]
        ] = {
            SupportedStreamTypes.DASH: DASHFFMpegConcat,
            SupportedStreamTypes.HLS: HLSFFMpegConcat,
            SupportedStreamTypes.DIRECT: DirectFileCompression,
        }

    async def mux(
        self,
        downloaded_media: DownloadedMedia,
        output_file_name: str | None = None,
    ) -> MuxedMedia:
        self._static_media_root.mkdir(parents=True, exist_ok=True)

        if not downloaded_media.chunks:
            raise MediaMuxNoChunksError(source_url=downloaded_media.source_url)

        output_stem = output_file_name or uuid4().hex
        output_path = self._static_media_root / f"{output_stem}.mp4"
        sorted_chunks = self._prepare_chunks(downloaded_media.chunks)
        command = self._build_command(
            downloaded_media.stream_type, sorted_chunks, output_path
        )

        await command.execute_command()
        return self._build_muxed_media(downloaded_media, output_path)

    def _build_command(
        self,
        stream_type: SupportedStreamTypes,
        chunks: list[DownloadedMediaChunk],
        output_path: Path,
    ) -> BaseFFMpegCommand:
        command_type = self._commands_by_stream_type.get(stream_type)
        if command_type is None:
            raise ValueError(f"Unsupported stream type: {stream_type}")

        return command_type(
            chunks=chunks,
            output_path=output_path,
            ffmpeg_binary=self._ffmpeg_binary,
            threads_to_use=self._resolve_thread_count(),
        )

    def _build_muxed_media(
        self,
        downloaded_media: DownloadedMedia,
        output_path: Path,
    ) -> MuxedMedia:
        static_prefix = config.media_static_url_prefix.rstrip("/")
        return MuxedMedia(
            source_url=downloaded_media.source_url,
            stream_type=downloaded_media.stream_type,
            output_path=output_path,
            static_url_path=f"{static_prefix}/{output_path.name}",
        )

    def _prepare_chunks(
        self,
        chunks: list[DownloadedMediaChunk],
    ) -> list[DownloadedMediaChunk]:
        if self._is_sorted(chunks):
            return chunks

        return sorted(chunks, key=self._chunk_sort_key)

    def _is_sorted(self, chunks: list[DownloadedMediaChunk]) -> bool:
        if len(chunks) < 2:
            return True

        return all(
            self._chunk_sort_key(chunks[index])
            <= self._chunk_sort_key(chunks[index + 1])
            for index in range(len(chunks) - 1)
        )

    def _chunk_sort_key(self, chunk: DownloadedMediaChunk) -> tuple[int, int]:
        initialization_order = 0 if chunk.is_initialization_segment else 1
        return (initialization_order, chunk.sequence_number)

    def _resolve_thread_count(self) -> int:
        if self._configured_threads is not None and self._configured_threads > 0:
            return self._configured_threads

        if config.ffmpeg_threads is not None and config.ffmpeg_threads > 0:
            return config.ffmpeg_threads

        return max(1, (os.cpu_count() or 1) // 2)
