import pytest

from core.errors import DirectMediaInvalidUrlError
from domain.media.supported_media_types import SupportedStreamTypes
from infrastructure.media.resolvers.direct_mp4_resolver import DirectMP4Resolver

pytestmark = pytest.mark.anyio


async def test_direct_resolver_resolves_single_link() -> None:
    resolver = DirectMP4Resolver()

    resolved_stream = await resolver.resolve_stream("https://example.com/video.mp4")

    assert resolved_stream.stream_type == SupportedStreamTypes.DIRECT
    assert resolved_stream.is_chunked is False
    assert len(resolved_stream.links) == 1
    assert resolved_stream.links[0].url == "https://example.com/video.mp4"


async def test_direct_resolver_can_resolve_non_manifest_url() -> None:
    resolver = DirectMP4Resolver()

    can_resolve = await resolver.can_resolve("https://example.com/video.webm")

    assert can_resolve is True


async def test_direct_resolver_rejects_manifest_urls() -> None:
    resolver = DirectMP4Resolver()

    assert await resolver.can_resolve("https://example.com/playlist.m3u8") is False
    assert await resolver.can_resolve("https://example.com/manifest.mpd") is False


async def test_direct_resolver_raises_custom_error_for_invalid_url() -> None:
    resolver = DirectMP4Resolver()

    with pytest.raises(DirectMediaInvalidUrlError):
        await resolver.resolve_stream("not-a-valid-url")
