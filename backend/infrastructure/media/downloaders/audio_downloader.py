from pathlib import Path

import httpx

from domain.media.protocols import AudioDownloaderProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, MediaDownloadableLink
from infrastructure.media.downloaders.general_downloader import GeneralDownloader


class AudioDownloader(GeneralDownloader, AudioDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        chunks_data: list[MediaDownloadableLink],
        source_url: str,
        stream_type: SupportedStreamTypes = SupportedStreamTypes.DIRECT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            path_to_download=path_to_download,
            chunks_data=chunks_data,
            stream_type=stream_type,
            source_url=source_url,
            client=client,
        )
        self.audio_urls = self.download_urls

    async def download_audio(self) -> DownloadedMedia:
        return await self._download_media()
