from urllib.parse import urlparse

from core.errors import DirectMediaInvalidUrlError
from domain.media.protocols import StreamResolverProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink, ResolvedMediaStream


class DirectMP4Resolver(StreamResolverProtocol):
    stream_type: SupportedStreamTypes = SupportedStreamTypes.DIRECT

    async def can_resolve(self, stream_url: str) -> bool:
        lowered = stream_url.lower()
        return not lowered.endswith(".m3u8") and not lowered.endswith(".mpd")

    async def resolve_stream(self, video_to_resolve: str) -> ResolvedMediaStream:
        parsed = urlparse(video_to_resolve)
        if not parsed.scheme or not parsed.netloc:
            raise DirectMediaInvalidUrlError(media_url=video_to_resolve)

        return ResolvedMediaStream(
            source_url=video_to_resolve,
            stream_type=self.stream_type,
            is_chunked=False,
            links=[
                MediaDownloadableLink(
                    url=video_to_resolve,
                    sequence_number=0,
                    is_initialization_segment=False,
                )
            ],
        )
