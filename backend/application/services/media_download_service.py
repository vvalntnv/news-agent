from typing import Protocol

from application.background_jobs.payloads import (
    MediaDownloadJobOutput,
    MediaDownloadJobPayload,
    MediaDownloadJobResult,
)
from application.media_download_handler import MediaDownloadHandler
from domain.media.value_objects import MuxedMedia


class MediaDownloadHandlerProtocol(Protocol):
    async def download_media(self, source_urls: list[str]) -> list[MuxedMedia]: ...


class MediaDownloadService:
    def __init__(
        self,
        media_download_handler: MediaDownloadHandlerProtocol | None = None,
    ) -> None:
        self._media_download_handler = media_download_handler or MediaDownloadHandler()

    async def download_media(
        self,
        payload: MediaDownloadJobPayload,
    ) -> MediaDownloadJobResult:
        muxed_media = await self._media_download_handler.download_media(
            payload.source_urls
        )
        return MediaDownloadJobResult(
            outputs=[
                self._build_media_download_job_output(media_item)
                for media_item in muxed_media
            ]
        )

    def _build_media_download_job_output(
        self,
        muxed_media: MuxedMedia,
    ) -> MediaDownloadJobOutput:
        return MediaDownloadJobOutput(
            source_url=muxed_media.source_url,
            stream_type=muxed_media.stream_type,
            output_path=str(muxed_media.output_path),
            static_url_path=muxed_media.static_url_path,
        )
