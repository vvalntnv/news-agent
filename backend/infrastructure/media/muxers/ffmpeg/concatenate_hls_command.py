from __future__ import annotations

from pathlib import Path

from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMediaChunk

from .ffmpeg_command import BaseFFMpegCommand, FFMpegResult


class HLSFFMpegConcat(BaseFFMpegCommand):
    stream_type = SupportedStreamTypes.HLS

    def __init__(
        self,
        chunks: list[DownloadedMediaChunk],
        output_path: Path,
        ffmpeg_binary: str | None = None,
        threads_to_use: int | None = None,
    ) -> None:
        super().__init__(chunks, output_path, ffmpeg_binary, threads_to_use)

    async def execute_command(self) -> FFMpegResult:
        concat_file = self._output_path.with_suffix(".concat.txt")
        concat_lines = [
            f"file '{self._escape_concat_path(chunk.file_path)}'"
            for chunk in self._chunks
        ]
        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

        try:
            args = [
                self._ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                *self._build_common_output_args(),
            ]
            return await self._run_ffmpeg(args)
        finally:
            if concat_file.exists():
                concat_file.unlink()

    def _escape_concat_path(self, chunk_path: Path) -> str:
        return chunk_path.as_posix().replace("'", "\\'")
