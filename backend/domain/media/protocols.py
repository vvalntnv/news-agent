from pathlib import Path
from typing import Protocol, runtime_checkable

from domain.media.value_objects import (
    DownloadedMedia,
    MediaDownloadableLink,
    MuxedMedia,
    ResolvedMediaStream,
)


@runtime_checkable
class StreamResolverProtocol(Protocol):
    """
    Protocol for resolving stream URLs to concrete downloadable links.
    """

    async def can_resolve(self, stream_url: str) -> bool: ...

    async def resolve_stream(self, video_to_resolve: str) -> ResolvedMediaStream:
        """
        This method gets a url for a video stream and resolves the given
        manifest/file (if any) to produce downloadable links that can then
        be downloaded by the VideoDownloaderProtocol.
        """
        ...


@runtime_checkable
class VideoDownloaderProtocol(Protocol):
    """
    Protocol for downloading videos from resolved URLs.
    """

    path_to_download: Path | str
    """Path where downloaded files should be saved."""

    video_urls: list[MediaDownloadableLink]
    """Ordered list of URLs with metadata to download."""

    async def download_video(self) -> DownloadedMedia: ...


@runtime_checkable
class ImageDownloaderProtocol(Protocol):
    """
    Protocol for downloading images from resolved URLs.
    """

    path_to_download: Path | str
    """Path where downloaded files should be saved."""

    image_urls: list[MediaDownloadableLink]
    """List of image URLs with metadata to download."""

    async def download_image(self) -> DownloadedMedia: ...


@runtime_checkable
class AudioDownloaderProtocol(Protocol):
    """
    Protocol for downloading audio from resolved URLs.
    """

    path_to_download: Path | str
    """Path where downloaded files should be saved."""

    audio_urls: list[MediaDownloadableLink]
    """List of audio URLs with metadata to download."""

    async def download_audio(self) -> DownloadedMedia: ...


@runtime_checkable
class MediaMuxerProtocol(Protocol):
    """
    Protocol for muxing downloaded chunks/files into final media output.
    """

    async def mux(
        self,
        downloaded_media: DownloadedMedia,
        output_file_name: str | None = None,
    ) -> MuxedMedia: ...
