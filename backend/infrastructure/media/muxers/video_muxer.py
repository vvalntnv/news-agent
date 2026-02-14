from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

from core.config import config
from core.errors import FFmpegExecutionError, MediaMuxNoChunksError
from domain.media.protocols import MediaMuxerProtocol
from domain.media.value_objects import DownloadedMedia, DownloadedMediaChunk, MuxedMedia


class VideoMuxer(MediaMuxerProtocol):
    def __init__(
        self,
        static_media_root: Path | str | None = None,
        ffmpeg_binary: str | None = None,
        ffmpeg_threads: int | None = None,
    ) -> None:
        self._static_media_root = Path(static_media_root or config.media_static_root)
        self._ffmpeg_binary = ffmpeg_binary or config.ffmpeg_binary

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

        if len(sorted_chunks) == 1:
            ffmpeg_args = self._build_command_for_single_file(
                sorted_chunks[0].file_path,
                output_path,
                ffmpeg_threads,
            )
            return self._build_muxed_media(downloaded_media, output_path)

        return self._build_muxed_media(downloaded_media, output_path)

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

    async def _mux_multiple_files(
        self,
        sorted_chunks: list[DownloadedMediaChunk],
        output_path: Path,
        ffmpeg_threads: int,
    ) -> None:
        concat_file = output_path.with_suffix(".concat.txt")
        concat_lines = [
            f"file '{chunk.file_path.as_posix()}'" for chunk in sorted_chunks
        ]
        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")
        try:
            ffmpeg_args = self._build_command_for_multiple_files(
                concat_file,
                output_path,
                ffmpeg_threads,
            )
            await self._run_ffmpeg(ffmpeg_args)
        finally:
            if concat_file.exists():
                concat_file.unlink()

    def _build_command_for_single_file(
        self,
        input_file: Path,
        output_file: Path,
        ffmpeg_threads: int,
    ) -> list[str]:
        return [
            self._ffmpeg_binary,
            "-y",
            "-i",
            str(input_file),
            "-threads",
            str(ffmpeg_threads),
            *self._build_transcode_flags(),
            str(output_file),
        ]

    def _build_command_for_multiple_files(
        self,
        concat_file: Path,
        output_file: Path,
        ffmpeg_threads: int,
    ) -> list[str]:
        return [
            self._ffmpeg_binary,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-threads",
            str(ffmpeg_threads),
            *self._build_transcode_flags(),
            str(output_file),
        ]

    def _build_transcode_flags(self) -> list[str]:
        return [
            "-c:v",
            config.ffmpeg_video_codec,
            "-preset",
            config.ffmpeg_video_preset,
            "-crf",
            str(config.ffmpeg_video_crf),
            "-c:a",
            config.ffmpeg_audio_codec,
            "-b:a",
            config.ffmpeg_audio_bitrate,
            "-movflags",
            config.ffmpeg_movflags,
        ]

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
