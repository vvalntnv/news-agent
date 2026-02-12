from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from core.config import config
from core.errors import HlsManifestNoMediaSegmentsError, HlsManifestNoVariantsError
from domain.media.protocols import StreamResolverProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink, ResolvedMediaStream


class HlsM3U8Resolver(StreamResolverProtocol):
    stream_type: SupportedStreamTypes = SupportedStreamTypes.HLS

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            headers={
                "User-Agent": config.media_http_user_agent,
                "Accept": config.media_http_accept_hls,
            },
            follow_redirects=config.media_http_follow_redirects,
            timeout=config.media_http_timeout_seconds,
        )
        self._is_client_owned = client is None

    async def can_resolve(self, stream_url: str) -> bool:
        if stream_url.lower().endswith(".m3u8"):
            return True

        extension = Path(urlparse(stream_url).path).suffix.lower()
        if extension and extension != ".m3u8":
            return False

        try:
            response = await self._client.get(stream_url)
            response.raise_for_status()
        except httpx.HTTPError:
            return False

        payload = response.text.lstrip()
        return payload.startswith("#EXTM3U")

    async def resolve_stream(self, video_to_resolve: str) -> ResolvedMediaStream:
        media_playlist_url = await self._resolve_media_playlist_url(video_to_resolve)
        media_playlist_content = await self._load_playlist(media_playlist_url)

        links = self._parse_media_playlist(media_playlist_url, media_playlist_content)
        if not links:
            raise HlsManifestNoMediaSegmentsError(manifest_url=media_playlist_url)

        return ResolvedMediaStream(
            source_url=video_to_resolve,
            stream_type=self.stream_type,
            links=links,
            is_chunked=len(links) > 1,
        )

    async def close(self) -> None:
        if self._is_client_owned:
            await self._client.aclose()

    async def _resolve_media_playlist_url(self, playlist_url: str) -> str:
        playlist_content = await self._load_playlist(playlist_url)

        if "#EXT-X-STREAM-INF" not in playlist_content:
            return playlist_url

        playlist_lines = [
            line.strip() for line in playlist_content.splitlines() if line.strip()
        ]

        variants: list[tuple[int, str]] = []
        for line_index, line in enumerate(playlist_lines):
            if not line.startswith("#EXT-X-STREAM-INF"):
                continue

            attributes = self._parse_attributes(line)
            bandwidth_text = attributes.get("BANDWIDTH", "0")
            bandwidth = int(bandwidth_text) if bandwidth_text.isdigit() else 0

            next_line_index = line_index + 1
            if next_line_index >= len(playlist_lines):
                continue

            candidate_uri = playlist_lines[next_line_index]
            if candidate_uri.startswith("#"):
                continue

            variants.append((bandwidth, urljoin(playlist_url, candidate_uri)))

        if not variants:
            raise HlsManifestNoVariantsError(manifest_url=playlist_url)

        best_variant = max(variants, key=lambda item: item[0])
        return best_variant[1]

    async def _load_playlist(self, playlist_url: str) -> str:
        response = await self._client.get(playlist_url)
        response.raise_for_status()
        return response.text

    def _parse_media_playlist(
        self, playlist_url: str, playlist_content: str
    ) -> list[MediaDownloadableLink]:
        links: list[MediaDownloadableLink] = []
        playlist_lines = [
            line.strip() for line in playlist_content.splitlines() if line.strip()
        ]

        media_sequence = 0
        for line in playlist_lines:
            if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                _, sequence_value = line.split(":", maxsplit=1)
                if sequence_value.isdigit():
                    media_sequence = int(sequence_value)

            elif line.startswith("#EXT-X-MAP"):
                attributes = self._parse_attributes(line)
                init_uri = attributes.get("URI")
                if init_uri:
                    links.append(
                        MediaDownloadableLink(
                            url=urljoin(playlist_url, init_uri),
                            sequence_number=media_sequence,
                            is_initialization_segment=True,
                        )
                    )

            if line.startswith("#"):
                continue

            links.append(
                MediaDownloadableLink(
                    url=urljoin(playlist_url, line),
                    sequence_number=media_sequence,
                    is_initialization_segment=False,
                )
            )
            media_sequence += 1

        return links

    def _parse_attributes(self, line: str) -> dict[str, str]:
        if ":" not in line:
            return {}

        _, raw_attributes = line.split(":", maxsplit=1)
        parsed_attributes: dict[str, str] = {}

        current = ""
        tokens: list[str] = []
        quoted = False
        for char in raw_attributes:
            if char == '"':
                quoted = not quoted
                current += char
                continue

            if char == "," and not quoted:
                if current:
                    tokens.append(current)
                current = ""
                continue

            current += char

        if current:
            tokens.append(current)

        for token in tokens:
            if "=" not in token:
                continue

            key, value = token.split("=", maxsplit=1)
            parsed_attributes[key.strip()] = value.strip().strip('"')

        return parsed_attributes
