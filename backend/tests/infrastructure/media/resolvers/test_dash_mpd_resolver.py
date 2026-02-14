import pytest
import httpx

from core.errors import (
    DashManifestMissingAdaptationSetError,
    DashManifestMissingPeriodError,
)
from domain.media.supported_media_types import SupportedStreamTypes
from infrastructure.media.resolvers.dash_mpd_resolver import DashMPDResolver

pytestmark = pytest.mark.anyio


def _build_client(manifests: dict[str, str]) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = manifests.get(str(request.url))
        if payload is None:
            return httpx.Response(404, text="not found")

        return httpx.Response(200, text=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_dash_resolver_parses_segment_list() -> None:
    mpd_payload = """
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <Period>
    <AdaptationSet mimeType="video/mp4">
      <Representation id="video-1" bandwidth="600000">
        <BaseURL>video/</BaseURL>
        <SegmentList>
          <Initialization sourceURL="init.mp4" />
          <SegmentURL media="chunk-1.m4s" />
          <SegmentURL media="chunk-2.m4s" />
        </SegmentList>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""
    client = _build_client({"https://example.com/manifest.mpd": mpd_payload})
    resolver = DashMPDResolver(client=client)

    resolved_stream = await resolver.resolve_stream("https://example.com/manifest.mpd")

    assert resolved_stream.stream_type == SupportedStreamTypes.DASH
    assert resolved_stream.is_chunked is True
    assert [item.url for item in resolved_stream.links] == [
        "https://example.com/video/init.mp4",
        "https://example.com/video/chunk-1.m4s",
        "https://example.com/video/chunk-2.m4s",
    ]
    assert resolved_stream.links[0].is_initialization_segment is True
    await client.aclose()


async def test_dash_resolver_detects_mpd_without_extension() -> None:
    mpd_payload = """
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011">
  <Period>
    <AdaptationSet mimeType="video/mp4">
      <Representation id="v" bandwidth="1">
        <SegmentTemplate media="chunk-$Number$.m4s" duration="2" timescale="1" />
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""
    client = _build_client({"https://example.com/stream": mpd_payload})
    resolver = DashMPDResolver(client=client)

    assert await resolver.can_resolve("https://example.com/stream") is True
    await client.aclose()


async def test_dash_resolver_uses_single_representation_file_for_media_ranges() -> None:
    mpd_payload = """
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <Period>
    <AdaptationSet mimeType="video/mp4">
      <Representation id="1" bandwidth="2839326">
        <BaseURL>64dd48a468_1080_track1_dashinit.mp4</BaseURL>
        <SegmentList timescale="12800" duration="25600">
          <Initialization range="0-950" />
          <SegmentURL mediaRange="951-578678" indexRange="951-994" />
          <SegmentURL mediaRange="578679-1050919" indexRange="578679-578722" />
        </SegmentList>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""
    client = _build_client({"https://example.com/manifest.mpd": mpd_payload})
    resolver = DashMPDResolver(client=client)

    resolved_stream = await resolver.resolve_stream("https://example.com/manifest.mpd")

    assert resolved_stream.is_chunked is False
    assert len(resolved_stream.links) == 1
    assert (
        resolved_stream.links[0].url
        == "https://example.com/64dd48a468_1080_track1_dashinit.mp4"
    )
    await client.aclose()


async def test_dash_resolver_raises_custom_error_when_period_is_missing() -> None:
    mpd_payload = """
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <BaseURL>video/</BaseURL>
</MPD>
"""
    client = _build_client({"https://example.com/manifest.mpd": mpd_payload})
    resolver = DashMPDResolver(client=client)

    with pytest.raises(DashManifestMissingPeriodError):
        await resolver.resolve_stream("https://example.com/manifest.mpd")

    await client.aclose()


async def test_dash_resolver_raises_custom_error_when_adaptation_set_missing() -> None:
    mpd_payload = """
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static">
  <Period></Period>
</MPD>
"""
    client = _build_client({"https://example.com/manifest.mpd": mpd_payload})
    resolver = DashMPDResolver(client=client)

    with pytest.raises(DashManifestMissingAdaptationSetError):
        await resolver.resolve_stream("https://example.com/manifest.mpd")

    await client.aclose()


# This lil dude seems to be working
# Skipped becuase the url will not always be present
@pytest.mark.skip()
async def test_dash_resolver_with_real_world() -> None:
    video_manifest = "https://media09.vbox7.com/sl/mi1WT9ID2u4XwTQEu-ygRA/1771192800/7d/7d4b25d085/7d4b25d085.mpd"
    resolver = DashMPDResolver()

    stream_data = await resolver.resolve_stream(video_manifest)
    assert len(stream_data.links) > 0
    assert stream_data.links[0].url, "No url provided"
