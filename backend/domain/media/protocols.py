from typing import Protocol

from pathlib import Path
from .value_objects import VideoData, AudioData

type DownloadedVideoUrl = str
type DownloadedImageUrl = str
type DownloadedAudioUrl = str


class VideoDownloaderProtocol(Protocol):
    """
    Protocol for downloading videos from URLs.

    Implementations should handle downloading video content from
    provided URLs and saving them to a specified location.
    """

    path_to_download: Path | str
    """Path where downloaded videos should be saved."""

    video_urls: list[VideoData]
    """List of video URLs with associated metadata to download."""

    async def download_video(self) -> DownloadedVideoUrl:
        """
        Downloads the video and returns the local path/URL of the downloaded file.

        Returns:
            DownloadedVideoUrl: Path or URL to the downloaded video file.

        Raises:
            DownloadError: If the video download fails.
        """
        ...


class ImageDownloaderProtocol(Protocol):
    """
    Protocol for downloading images from URLs.

    Implementations should handle downloading image content from
    provided URLs and saving them to a specified location.
    """

    path_to_download: Path | str
    """Path where downloaded images should be saved."""

    image_urls: list[str]
    """List of image URLs to download."""

    async def download_image(self) -> DownloadedImageUrl:
        """
        Downloads the image and returns the local path/URL of the downloaded file.

        Returns:
            DownloadedImageUrl: Path or URL to the downloaded image file.

        Raises:
            DownloadError: If the image download fails.
        """
        ...


class AudioDownloaderProtocol(Protocol):
    """
    Protocol for downloading audio from URLs.

    Implementations should handle downloading audio content from
    provided URLs and saving them to a specified location.
    """

    path_to_download: Path | str
    """Path where downloaded audio files should be saved."""

    audio_urls: list[AudioData]
    """List of audio URLs with associated metadata to download."""

    async def download_audio(self) -> DownloadedAudioUrl:
        """
        Downloads the audio and returns the local path/URL of the downloaded file.

        Returns:
            DownloadedAudioUrl: Path or URL to the downloaded audio file.

        Raises:
            DownloadError: If the audio download fails.
        """
        ...
