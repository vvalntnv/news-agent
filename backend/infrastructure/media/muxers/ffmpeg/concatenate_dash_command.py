import asyncio
from pathlib import Path

import aiofiles

from core.config import config
from core.errors import (
    MediaMuxChunksDifferentExtensionsError,
    MediaMuxChunksInDifferentPathsError,
    MediaMuxMissingInitializationSegmentError,
)
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMediaChunk

from .ffmpeg_command import BaseFFMpegCommand, FFMpegResult


class DASHFFMpegConcat(BaseFFMpegCommand):
    stream_type = SupportedStreamTypes.DASH

    def __init__(
        self,
        chunks: list[DownloadedMediaChunk],
        output_path: Path,
        ffmpeg_binary: str | None = None,
        threads_to_use: int | None = None,
    ) -> None:
        super().__init__(chunks, output_path, ffmpeg_binary, threads_to_use)
        self._files: list[Path] | None = None

    async def execute_command(self) -> FFMpegResult:
        self._assert_all_chunks_are_in_the_same_place()
        init_file = self._get_init_chunk()
        media_chunks = [
            chunk for chunk in self._chunks if not chunk.is_initialization_segment
        ]
        # This makes sure that the initial file is always first
        self._files = [
            init_file.file_path,
            *[chunk.file_path for chunk in media_chunks],
        ]

        args = [
            self._ffmpeg_binary,
            "-y",
            "-i",
            "pipe:0",
            *self._build_common_output_args(),
        ]

        return await self._run_ffmpeg(args)

    async def _run_ffmpeg(self, ffmpeg_args: list[str]) -> FFMpegResult:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
        )

        assert self._files is not None, "No files extracted (not possible)"
        assert process.stdin is not None, "stdin should always be opened"

        for file_path in self._files:
            async with aiofiles.open(file_path, "rb") as file:
                while True:
                    data = await file.read(config.dash_concat_chunk_size_bytes)
                    if not data:
                        break

                    process.stdin.write(data)
                    await process.stdin.drain()

        process.stdin.close()
        await process.stdin.wait_closed()

        stderr = await self._handle_process(process, ffmpeg_args)
        return FFMpegResult(
            stderr=stderr,
            output_path=self._output_path,
        )

    def _assert_all_chunks_are_in_the_same_place(self) -> None:
        for chunk_id in range(1, len(self._chunks)):
            curr_chunk = self._chunks[chunk_id]
            prev_chunk = self._chunks[chunk_id - 1]

            if curr_chunk.file_path.parent != prev_chunk.file_path.parent:
                raise MediaMuxChunksInDifferentPathsError(
                    str(curr_chunk.file_path.parent),
                    str(prev_chunk.file_path.parent),
                )

            if (
                curr_chunk.is_initialization_segment
                or prev_chunk.is_initialization_segment
            ):
                continue

            if curr_chunk.file_path.suffix != prev_chunk.file_path.suffix:
                raise MediaMuxChunksDifferentExtensionsError(
                    curr_chunk.file_path.suffix,
                    prev_chunk.file_path.suffix,
                )

    def _get_init_chunk(self) -> DownloadedMediaChunk:
        for chunk in self._chunks:
            if chunk.is_initialization_segment:
                return chunk

        raise MediaMuxMissingInitializationSegmentError(len(self._chunks))
