from typing import Protocol, runtime_checkable

from pathlib import Path

from domain.media.supported_media_types import SupportedStreamTypes
from .value_objects import VideoData, AudioData, MediaDownloadableLink

type DownloadedVideoFolderPath = Path
type DownloadedImageFolderPath = Path
type DownloadedAudioFolderPath = Path


@runtime_checkable
class StreamResolverProtocol(Protocol):

    stream_type: SupportedStreamTypes

    # Might want to transform that into a dict?
    # The video can either be a web url
    async def resolve_stream(
        self,
        video_to_resolve: str,
    ) -> list[MediaDownloadableLink]:
        """
        This method gets a url for a video streams and then resolves the
        given manifest file (if any) to produce downloadable links, that
        then can be downloaded by the VideoDownloaderProtocol
        """
        ...


@runtime_checkable
class VideoDownloaderProtocol(Protocol):
    """
    Protocol for downloading videos from URLs.

    Implementations should handle downloading video content from
    provided URLs and saving them to a specified location.
    """

    path_to_download: Path | str
    """Path where downloaded videos should be saved."""

    video_urls: list[MediaDownloadableLink]
    """List of video URLs with associated metadata to download."""

    async def download_video(self) -> DownloadedVideoFolderPath:
        """
        Downloads the video and returns the local path/URL of the downloaded file.

        Returns:
            DownloadedVideoUrl: Path or URL to the downloaded video file.

        Raises:
            DownloadError: If the video download fails.
        """
        ...


@runtime_checkable
class ImageDownloaderProtocol(Protocol):
    """
    Protocol for downloading images from URLs.

    Implementations should handle downloading image content from
    provided URLs and saving them to a specified location.
    """

    path_to_download: Path | str
    """Path where downloaded images should be saved."""

    image_urls: list[MediaDownloadableLink]
    """List of image URLs to download."""

    async def download_image(self) -> DownloadedImageFolderPath:
        """
        Downloads the image and returns the local path/URL of the downloaded file.

        Returns:
            DownloadedImageUrl: Path or URL to the downloaded image file.

        Raises:
            DownloadError: If the image download fails.
        """
        ...


@runtime_checkable
class AudioDownloaderProtocol(Protocol):
    """
    Protocol for downloading audio from URLs.

    Implementations should handle downloading audio content from
    provided URLs and saving them to a specified location.
    """

    path_to_download: Path | str
    """Path where downloaded audio files should be saved."""

    audio_urls: list[MediaDownloadableLink]
    """List of audio URLs with associated metadata to download."""

    async def download_audio(self) -> DownloadedAudioFolderPath:
        """
        Downloads the audio and returns the local path/URL of the downloaded file.

        Returns:
            DownloadedAudioUrl: Path or URL to the downloaded audio file.

        Raises:
            DownloadError: If the audio download fails.
        """
        ...
