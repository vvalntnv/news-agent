from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from core.config import config
from domain.media.protocols import VideoDownloaderProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import (
    DownloadedMedia,
    DownloadedMediaChunk,
    MediaDownloadableLink,
)


class VideoDownloader(VideoDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        chunks_data: list[MediaDownloadableLink],
        stream_type: SupportedStreamTypes,
        source_url: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.path_to_download = path_to_download
        self.video_urls = chunks_data
        self._stream_type = stream_type
        self._source_url = source_url
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": config.media_http_user_agent},
            follow_redirects=config.media_http_follow_redirects,
            timeout=config.media_http_timeout_seconds,
        )
        self._is_client_owned = client is None

    async def download_video(self) -> DownloadedMedia:
        download_dir = Path(self.path_to_download)
        download_dir.mkdir(parents=True, exist_ok=True)

        ordered_urls = self._prepare_ordered_urls()

        downloaded_chunks: list[DownloadedMediaChunk] = []
        try:
            for index, chunk in enumerate(ordered_urls):
                downloaded_chunks.append(
                    await self._download_chunk(
                        chunk=chunk,
                        chunk_index=index,
                        download_dir=download_dir,
                    )
                )
        finally:
            if self._is_client_owned:
                await self._client.aclose()

        return DownloadedMedia(
            source_url=self._source_url,
            stream_type=self._stream_type,
            chunks=downloaded_chunks,
        )

    def _extract_extension(self, url: str) -> str:
        parsed = urlparse(url)
        extension = Path(parsed.path).suffix
        if extension:
            return extension

        return ".bin"

    async def _download_chunk(
        self,
        chunk: MediaDownloadableLink,
        chunk_index: int,
        download_dir: Path,
    ) -> DownloadedMediaChunk:
        response = await self._client.get(chunk.url)
        response.raise_for_status()

        extension = self._extract_extension(chunk.url)
        segment_label = "init" if chunk.is_initialization_segment else "chunk"
        file_name = f"{chunk_index:05d}_{segment_label}{extension}"
        file_path = download_dir / file_name
        file_path.write_bytes(response.content)

        return DownloadedMediaChunk(
            source_url=chunk.url,
            file_path=file_path,
            sequence_number=chunk.sequence_number,
            is_initialization_segment=chunk.is_initialization_segment,
        )

    def _prepare_ordered_urls(self) -> list[MediaDownloadableLink]:
        if self._is_sorted(self.video_urls):
            return self.video_urls

        return sorted(self.video_urls, key=self._sort_key)

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
