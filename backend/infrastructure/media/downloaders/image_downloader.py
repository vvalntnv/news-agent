from pathlib import Path

import httpx

from domain.media.protocols import ImageDownloaderProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, MediaDownloadableLink
from infrastructure.media.downloaders.general_downloader import GeneralDownloader


class ImageDownloader(GeneralDownloader, ImageDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        image_urls: list[MediaDownloadableLink],
        source_url: str,
        stream_type: SupportedStreamTypes = SupportedStreamTypes.DIRECT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            path_to_download=path_to_download,
            chunks_data=image_urls,
            stream_type=stream_type,
            source_url=source_url,
            client=client,
        )
        self.image_urls = self.download_urls

    async def download_image(self) -> DownloadedMedia:
        return await self._download_media()
