from __future__ import annotations

from pathlib import Path

from core.errors import MediaMuxDirectRequiresSingleChunkError
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMediaChunk

from .ffmpeg_command import BaseFFMpegCommand, FFMpegResult


class DirectFileCompression(BaseFFMpegCommand):
    stream_type = SupportedStreamTypes.DIRECT

    def __init__(
        self,
        chunks: list[DownloadedMediaChunk],
        output_path: Path,
        ffmpeg_binary: str | None = None,
        threads_to_use: int | None = None,
    ) -> None:
        super().__init__(chunks, output_path, ffmpeg_binary, threads_to_use)

    async def execute_command(self) -> FFMpegResult:
        if len(self._chunks) != 1:
            raise MediaMuxDirectRequiresSingleChunkError(chunk_count=len(self._chunks))

        input_file = self._chunks[0].file_path
        args = [
            self._ffmpeg_binary,
            "-y",
            "-i",
            str(input_file),
            *self._build_common_output_args(),
        ]
        return await self._run_ffmpeg(args)
