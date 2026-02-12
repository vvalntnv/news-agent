from pathlib import Path
from domain.media.protocols import StreamResolverProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink


class DashMPDResolver(StreamResolverProtocol):
    stream_type: SupportedStreamTypes = SupportedStreamTypes.DASH

    async def resolve_stream(
        self,
        video_to_resolve: str,
    ) -> list[MediaDownloadableLink]:

        return [
            MediaDownloadableLink(
                size_in_bytes=100,
                url="http://test.com/videko",  # type: ignore
            )
        ]
