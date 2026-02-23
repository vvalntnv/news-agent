from pathlib import Path

import httpx

from domain.media.protocols import VideoDownloaderProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, MediaDownloadableLink
from infrastructure.media.downloaders.general_downloader import GeneralDownloader


class VideoDownloader(GeneralDownloader, VideoDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        chunks_data: list[MediaDownloadableLink],
        stream_type: SupportedStreamTypes,
        source_url: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            path_to_download=path_to_download,
            chunks_data=chunks_data,
            stream_type=stream_type,
            source_url=source_url,
            client=client,
        )
        self.video_urls = self.download_urls

    async def download_video(self) -> DownloadedMedia:
        return await self._download_media()
