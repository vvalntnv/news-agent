from pathlib import Path

from domain.media.protocols import (
    ImageDownloaderProtocol,
    VideoDownloaderFactoryProtocol,
)
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, MediaDownloadableLink
from infrastructure.media.downloaders.video_downloader import VideoDownloader


class ImageDownloader(ImageDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        image_urls: list[MediaDownloadableLink],
        source_url: str,
        video_downloader_factory: VideoDownloaderFactoryProtocol | None = None,
    ) -> None:
        self.path_to_download = path_to_download
        self.image_urls = image_urls
        self._source_url = source_url
        self._video_downloader_factory = video_downloader_factory

    async def download_image(self) -> DownloadedMedia:
        factory = self._video_downloader_factory or VideoDownloader
        delegated_downloader = factory(
            path_to_download=self.path_to_download,
            chunks_data=self.image_urls,
            stream_type=SupportedStreamTypes.DIRECT,
            source_url=self._source_url,
        )
        return await delegated_downloader.download_video()
