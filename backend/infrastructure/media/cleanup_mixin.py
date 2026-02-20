from __future__ import annotations

import asyncio
from pathlib import Path

from domain.media.value_objects import DownloadedMedia, DownloadedMediaChunk


class MediaCleanupMixin:
    async def _remove_downloaded_media(
        self, target: DownloadedMedia | list[DownloadedMediaChunk] | list[Path]
    ) -> None:
        """
        Removes downloaded chunks and their parent directory asynchronously.
        Accepts DownloadedMedia object, list of DownloadedMediaChunk or list of Paths.
        """
        paths: list[Path] = []
        if isinstance(target, DownloadedMedia):
            paths = [chunk.file_path for chunk in target.chunks]
        elif isinstance(target, list):
            if not target:
                return
            if isinstance(target[0], DownloadedMediaChunk):
                paths = [chunk.file_path for chunk in target]  # type: ignore
            elif isinstance(target[0], Path):
                paths = target  # type: ignore

        if not paths:
            return

        # Parallel file deletion
        deletion_tasks = [asyncio.to_thread(self._remove_file, path) for path in paths]
        await asyncio.gather(*deletion_tasks)

        # Remove the directories if they are empty
        parent_dirs = {path.parent for path in paths}
        for parent_dir in parent_dirs:
            await asyncio.to_thread(self._remove_dir_if_empty, parent_dir)

    def _remove_file(self, file_path: Path) -> None:
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass

    def _remove_dir_if_empty(self, dir_path: Path) -> None:
        try:
            if dir_path.exists() and not any(dir_path.iterdir()):
                dir_path.rmdir()
        except (OSError, StopIteration):
            pass
