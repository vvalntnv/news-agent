import asyncio
from asyncio.subprocess import Process
import os
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, DirectoryPath

from core.config import config
from core.errors.media_related import FFmpegExecutionError
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMediaChunk


class FFMpegResult(BaseModel):
    stderr: str | None
    output_dir: DirectoryPath


class BaseFFMpegCommand(ABC):
    def __init__(
        self,
        chunks: list[DownloadedMediaChunk],
        output_path: Path,
        threads_to_use: int | None = None,
    ) -> None:
        self._ffmpeg_binary = config.ffmpeg_binary
        self._chunks = chunks

        assert output_path.is_file()
        self._output_path = output_path

        self._threads_to_use = threads_to_use or self._resolve_thread_count()

    stream_type: SupportedStreamTypes

    @abstractmethod
    async def execute_command(self) -> FFMpegResult:
        """
        Executes the ffmpeg command
        """
        ...

    def _resolve_thread_count(self) -> int:
        if config.ffmpeg_threads is not None and config.ffmpeg_threads > 0:
            return config.ffmpeg_threads

        return max(1, (os.cpu_count() or 1) // 2)

    async def _run_ffmpeg(self, ffmpeg_args: list[str]) -> FFMpegResult:
        """
        Runs an ffmpeg command (asynchronously).
        Returns the captured stderr
        """
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stderr = await self._handle_process(process, ffmpeg_args)

        return FFMpegResult(
            stderr=str(stderr),
            output_dir=self._output_path,  # type: ignore
        )

    async def _handle_process(self, process: Process, ffmpeg_args: list[str]) -> bytes:
        # Stdout
        _, stderr = await process.communicate()
        if process.returncode != 0:
            decoded_error = stderr.decode("utf-8", errors="ignore")
            return_code = process.returncode if process.returncode is not None else -1
            raise FFmpegExecutionError(
                command=ffmpeg_args,
                return_code=return_code,
                stderr=decoded_error,
            )

        return stderr
