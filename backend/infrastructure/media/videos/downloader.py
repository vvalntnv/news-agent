from os import path
from domain.media.protocols import VideoDownloaderProtocol
from domain.media.value_objects import VideoData
from pathlib import Path


class VideoDownloader(VideoDownloaderProtocol):
    def __init__(
        self,
        path_to_download: Path | str,
        videos_to_download: list[VideoData],
    ) -> None:
        self.path_to_download = path_to_download
        self.video_urls = videos_to_download
        super().__init__()

    async def download_video(self) -> str:
        return "https://ph.com/static/bdsm.video"
