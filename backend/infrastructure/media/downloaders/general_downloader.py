from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import httpx

from core.config import config
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import (
    DownloadedMedia,
    DownloadedMediaChunk,
    MediaDownloadableLink,
)
from infrastructure.media.cleanup_mixin import MediaCleanupMixin
from infrastructure.media.downloaders.async_retry_job_pool import (
    AsyncRetryJobPool,
    RetryJob,
)
from infrastructure.media.downloaders.retry_policy import RetryPolicy


class GeneralDownloader(MediaCleanupMixin):
    def __init__(
        self,
        path_to_download: Path | str,
        chunks_data: list[MediaDownloadableLink],
        stream_type: SupportedStreamTypes,
        source_url: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.path_to_download = path_to_download
        self.download_urls = chunks_data
        self._stream_type = stream_type
        self._source_url = source_url
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": config.media_http_user_agent},
            follow_redirects=config.media_http_follow_redirects,
            timeout=config.media_http_timeout_seconds,
        )
        self._is_client_owned = client is None

    async def _download_media(self) -> DownloadedMedia:
        download_dir = Path(self.path_to_download)
        download_dir.mkdir(parents=True, exist_ok=True)

        ordered_urls = self._prepare_ordered_urls()

        try:
            downloaded_chunks = await self._download_chunks(
                ordered_urls=ordered_urls,
                download_dir=download_dir,
            )
        except Exception:
            await self._cleanup_failed_download(download_dir)
            raise
        finally:
            if self._is_client_owned:
                await self._client.aclose()

        return DownloadedMedia(
            source_url=self._source_url,
            stream_type=self._stream_type,
            chunks=downloaded_chunks,
        )

    async def _download_chunks(
        self,
        ordered_urls: list[MediaDownloadableLink],
        download_dir: Path,
    ) -> list[DownloadedMediaChunk]:
        jobs = [
            self._build_chunk_job(chunk, index, download_dir)
            for index, chunk in enumerate(ordered_urls)
        ]
        if not jobs:
            return []

        pool = AsyncRetryJobPool[DownloadedMediaChunk](
            jobs=jobs,
            policy=self._build_retry_policy(),
            concurrency=config.media_download_max_concurrency,
        )
        return await pool.run()

    async def _cleanup_failed_download(self, download_dir: Path) -> None:
        files_to_delete = list(download_dir.iterdir())
        await self._remove_downloaded_media(files_to_delete)

        if download_dir.exists() and not files_to_delete:
            self._remove_dir_if_empty(download_dir)

    def _build_retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            max_attempts=config.media_download_retry_max_attempts,
            base_backoff_seconds=config.media_download_retry_base_backoff_seconds,
            max_backoff_seconds=config.media_download_retry_max_backoff_seconds,
            jitter_ratio=config.media_download_retry_jitter_ratio,
            retryable_status_codes=config.media_download_retryable_status_codes,
            fallback_penalty_seconds=config.media_download_retry_fallback_penalty_seconds,
        )

    def _build_chunk_job(
        self,
        chunk: MediaDownloadableLink,
        chunk_index: int,
        download_dir: Path,
    ) -> RetryJob[DownloadedMediaChunk]:
        extension = self._extract_extension(chunk.url)
        segment_label = "init" if chunk.is_initialization_segment else "chunk"
        file_name = f"{chunk_index:05d}_{segment_label}{extension}"
        file_path = download_dir / file_name

        async def attempt() -> DownloadedMediaChunk:
            await self._remove_partial_file_if_exists(file_path)
            try:
                async with self._client.stream("GET", chunk.url) as stream:
                    stream.raise_for_status()

                    async with aiofiles.open(file_path, "wb") as file:
                        async for content in stream.aiter_bytes():
                            await file.write(content)
            except Exception:
                await self._remove_partial_file_if_exists(file_path)
                raise

            return DownloadedMediaChunk(
                source_url=chunk.url,
                file_path=file_path,
                sequence_number=chunk.sequence_number,
                is_initialization_segment=chunk.is_initialization_segment,
            )

        return RetryJob(id=file_name, attempt=attempt)

    async def _remove_partial_file_if_exists(self, file_path: Path) -> None:
        if not file_path.exists():
            return

        await asyncio.to_thread(self._remove_file, file_path)

    def _extract_extension(self, url: str) -> str:
        parsed = urlparse(url)
        extension = Path(parsed.path).suffix
        if extension:
            return extension

        return ".bin"

    def _prepare_ordered_urls(self) -> list[MediaDownloadableLink]:
        if self._is_sorted(self.download_urls):
            return self.download_urls

        return sorted(self.download_urls, key=self._sort_key)

    def _is_sorted(self, links: list[MediaDownloadableLink]) -> bool:
        if len(links) < 2:
            return True

        return all(
            self._sort_key(links[index]) <= self._sort_key(links[index + 1])
            for index in range(len(links) - 1)
        )

    def _sort_key(self, link: MediaDownloadableLink) -> tuple[int, int]:
        initialization_order = 0 if link.is_initialization_segment else 1
        return (initialization_order, link.sequence_number)
