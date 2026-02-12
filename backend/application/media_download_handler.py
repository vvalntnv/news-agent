from __future__ import annotations

import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from uuid import uuid4

from core.config import config
from domain.media.protocols import (
    MediaMuxerProtocol,
    StreamResolverProtocol,
    VideoDownloaderProtocol,
)
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink, MuxedMedia
from infrastructure.media.downloaders.video_downloader import VideoDownloader
from infrastructure.media.muxers.video_muxer import VideoMuxer
from infrastructure.media.resolvers.dash_mpd_resolver import DashMPDResolver
from infrastructure.media.resolvers.direct_mp4_resolver import DirectMP4Resolver
from infrastructure.media.resolvers.hls_m3u8_resolver import HlsM3U8Resolver

type VideoDownloaderFactory = Callable[
    [Path, list[MediaDownloadableLink], SupportedStreamTypes, str],
    VideoDownloaderProtocol,
]


class MediaDownloadHandler:
    def __init__(
        self,
        resolvers: list[StreamResolverProtocol] | None = None,
        muxer: MediaMuxerProtocol | None = None,
        download_root: Path | str = config.media_download_root,
        static_media_root: Path | str = config.media_static_root,
        downloader_factory: VideoDownloaderFactory | None = None,
    ) -> None:
        self._download_root = Path(download_root)
        self._download_root.mkdir(parents=True, exist_ok=True)

        self._resolvers = resolvers or [
            HlsM3U8Resolver(),
            DashMPDResolver(),
            DirectMP4Resolver(),
        ]
        self._muxer = muxer or VideoMuxer(static_media_root=static_media_root)
        self._downloader_factory = (
            downloader_factory or self._default_downloader_factory
        )

    async def download_media(self, source_urls: list[str]) -> list[MuxedMedia]:
        outputs: list[MuxedMedia] = []
        for source_url in source_urls:
            outputs.append(await self.download_single(source_url))

        return outputs

    async def download_single(self, source_url: str) -> MuxedMedia:
        resolver = await self._select_resolver(source_url)
        resolved_stream = await resolver.resolve_stream(source_url)

        download_path = self._download_root / uuid4().hex
        downloader = self._downloader_factory(
            download_path,
            resolved_stream.links,
            resolved_stream.stream_type,
            resolved_stream.source_url,
        )
        downloaded_media = await downloader.download_video()

        output_file_name = self._build_output_name(source_url)
        return await self._muxer.mux(
            downloaded_media, output_file_name=output_file_name
        )

    async def _select_resolver(self, source_url: str) -> StreamResolverProtocol:
        for resolver in self._resolvers:
            if await resolver.can_resolve(source_url):
                return resolver

        raise ValueError(f"No resolver can handle url: {source_url}")

    def _default_downloader_factory(
        self,
        path_to_download: Path,
        chunks_data: list[MediaDownloadableLink],
        stream_type: SupportedStreamTypes,
        source_url: str,
    ) -> VideoDownloaderProtocol:
        return VideoDownloader(
            path_to_download=path_to_download,
            chunks_data=chunks_data,
            stream_type=stream_type,
            source_url=source_url,
        )

    def _build_output_name(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        candidate = Path(parsed.path).stem.strip()
        if not candidate:
            return uuid4().hex

        normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate)
        return normalized or uuid4().hex
