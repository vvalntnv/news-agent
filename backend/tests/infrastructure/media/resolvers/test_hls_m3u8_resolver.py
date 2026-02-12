import pytest
import httpx

from core.errors import HlsManifestNoMediaSegmentsError, HlsManifestNoVariantsError
from domain.media.supported_media_types import SupportedStreamTypes
from infrastructure.media.resolvers.hls_m3u8_resolver import HlsM3U8Resolver

pytestmark = pytest.mark.anyio


def _build_client(playlists: dict[str, str]) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = playlists.get(str(request.url))
        if payload is None:
            return httpx.Response(404, text="not found")

        return httpx.Response(200, text=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_hls_resolver_selects_highest_bandwidth_variant() -> None:
    playlists = {
        "https://example.com/master.m3u8": "\n".join(
            [
                "#EXTM3U",
                "#EXT-X-STREAM-INF:BANDWIDTH=120000",
                "low/playlist.m3u8",
                "#EXT-X-STREAM-INF:BANDWIDTH=320000",
                "high/playlist.m3u8",
            ]
        ),
        "https://example.com/high/playlist.m3u8": "\n".join(
            [
                "#EXTM3U",
                "#EXT-X-MEDIA-SEQUENCE:10",
                '#EXT-X-MAP:URI="init.mp4"',
                "#EXTINF:4.0,",
                "seg-10.ts",
                "#EXTINF:4.0,",
                "seg-11.ts",
            ]
        ),
    }
    client = _build_client(playlists)
    resolver = HlsM3U8Resolver(client=client)

    resolved_stream = await resolver.resolve_stream("https://example.com/master.m3u8")

    assert resolved_stream.stream_type == SupportedStreamTypes.HLS
    assert resolved_stream.is_chunked is True
    assert [link.url for link in resolved_stream.links] == [
        "https://example.com/high/init.mp4",
        "https://example.com/high/seg-10.ts",
        "https://example.com/high/seg-11.ts",
    ]
    assert resolved_stream.links[0].is_initialization_segment is True
    assert resolved_stream.links[1].sequence_number == 10
    await client.aclose()


async def test_hls_resolver_detects_hls_payload_without_extension() -> None:
    playlists = {
        "https://example.com/stream": "\n".join(
            [
                "#EXTM3U",
                "#EXTINF:4.0,",
                "seg-1.ts",
            ]
        )
    }
    client = _build_client(playlists)
    resolver = HlsM3U8Resolver(client=client)

    assert await resolver.can_resolve("https://example.com/stream") is True
    await client.aclose()


async def test_hls_resolver_raises_custom_error_for_invalid_master() -> None:
    playlists = {
        "https://example.com/master.m3u8": "\n".join(
            [
                "#EXTM3U",
                "#EXT-X-STREAM-INF:BANDWIDTH=320000",
                "#EXT-X-ENDLIST",
            ]
        )
    }
    client = _build_client(playlists)
    resolver = HlsM3U8Resolver(client=client)

    with pytest.raises(HlsManifestNoVariantsError):
        await resolver.resolve_stream("https://example.com/master.m3u8")

    await client.aclose()


async def test_hls_resolver_raises_custom_error_for_empty_media_playlist() -> None:
    playlists = {
        "https://example.com/media.m3u8": "\n".join(
            [
                "#EXTM3U",
                "#EXT-X-ENDLIST",
            ]
        )
    }
    client = _build_client(playlists)
    resolver = HlsM3U8Resolver(client=client)

    with pytest.raises(HlsManifestNoMediaSegmentsError):
        await resolver.resolve_stream("https://example.com/media.m3u8")

    await client.aclose()
