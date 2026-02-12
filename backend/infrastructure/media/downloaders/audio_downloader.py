from pathlib import Path

from domain.media.protocols import AudioDownloaderProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import DownloadedMedia, MediaDownloadableLink
from infrastructure.media.downloaders.video_downloader import VideoDownloader


class AudioDownloader(AudioDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        chunks_data: list[MediaDownloadableLink],
        source_url: str,
    ) -> None:
        self.path_to_download = path_to_download
        self.audio_urls = chunks_data
        self._source_url = source_url

    async def download_audio(self) -> DownloadedMedia:
        # TODO: Implement dedicated audio-only downloading logic.
        delegated_downloader = VideoDownloader(
            path_to_download=self.path_to_download,
            chunks_data=self.audio_urls,
            stream_type=SupportedStreamTypes.DIRECT,
            source_url=self._source_url,
        )
        return await delegated_downloader.download_video()
