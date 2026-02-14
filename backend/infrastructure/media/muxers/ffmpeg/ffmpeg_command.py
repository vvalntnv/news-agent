from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from asyncio.subprocess import Process
from pathlib import Path

from pydantic import BaseModel

from core.config import config
from core.errors.media_related import FFmpegExecutionError
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMediaChunk


class FFMpegResult(BaseModel):
    stderr: str | None
    output_path: Path


class BaseFFMpegCommand(ABC):
    def __init__(
        self,
        chunks: list[DownloadedMediaChunk],
        output_path: Path,
        ffmpeg_binary: str | None = None,
        threads_to_use: int | None = None,
    ) -> None:
        self._ffmpeg_binary = ffmpeg_binary or config.ffmpeg_binary
        self._chunks = chunks
        self._output_path = output_path
        if threads_to_use is not None and threads_to_use > 0:
            self._threads_to_use = threads_to_use
        else:
            self._threads_to_use = self._resolve_thread_count()

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
            stderr=stderr,
            output_path=self._output_path,
        )

    async def _handle_process(self, process: Process, ffmpeg_args: list[str]) -> str:
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

        return stderr.decode("utf-8", errors="ignore")

    def _build_common_output_args(self) -> list[str]:
        return [
            "-threads",
            str(self._threads_to_use),
            *self._build_transcode_flags(),
            str(self._output_path),
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
