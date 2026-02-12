from pathlib import Path
from domain.media.protocols import VideoDownloaderProtocol
from domain.media.value_objects import MediaDownloadableLink


class VideoDownloader(VideoDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        chunks_data: list[MediaDownloadableLink],
    ) -> None:
        self.path_to_download = path_to_download
        self.video_urls = chunks_data

    async def download_video(self) -> str:
        return "test"
