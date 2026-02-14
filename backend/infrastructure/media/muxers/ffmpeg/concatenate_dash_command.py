import asyncio
import glob
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
        threads_to_use: int | None = None,
    ) -> None:
        super().__init__(chunks, output_path, threads_to_use)
        self._files = None

    async def execute_command(self) -> FFMpegResult:
        self._assert_all_chunks_are_in_the_same_place()
        last_chunk = self._chunks[-1]

        files_path = last_chunk.file_path.absolute()
        files_suffix = last_chunk.file_path.suffix

        init_file = self._get_init_chunk()
        chunks = sorted(glob.glob(f"{str(files_path)}/*.{files_suffix}"))
        self._files = [str(init_file.file_path)] + chunks

        args = [
            self._ffmpeg_binary,
            "-y",
            "-i",
            "-pipe:0",  # Wait for bytes to be pushed via the stdin
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "movflags",
            "+faststart",
            self._output_path,
        ]

        return await self._run_ffmpeg(args)

    async def _run_ffmpeg(self, ffmpeg_args: list[str]) -> FFMpegResult:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_args,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
        )

        assert self._files is not None, "No files extracted (not possible)"
        assert process.stdin is not None, "stdin should always be opened"

        for file_name in self._files:
            async with aiofiles.open(file_name, "rb") as file:
                while True:
                    data = await file.read(config.dash_concat_chunk_size_bytes)
                    if not data:
                        break

                    process.stdin.write(data)

        stderr = await self._handle_process(process, ffmpeg_args)
        return FFMpegResult(
            stderr=str(stderr),
            output_dir=self._output_path.parent,
        )

    def _assert_all_chunks_are_in_the_same_place(self) -> None:
        for chunk_id in range(1, len(self._chunks)):
            curr_chunk = self._chunks[chunk_id]
            prev_chunk = self._chunks[chunk_id - 1]

            if not curr_chunk.file_path.samefile(prev_chunk.file_path):
                raise MediaMuxChunksInDifferentPathsError(
                    str(curr_chunk.file_path),
                    str(prev_chunk.file_path),
                )

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
