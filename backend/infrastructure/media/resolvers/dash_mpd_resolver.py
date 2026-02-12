from __future__ import annotations

import math
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx

from core.config import config
from core.errors import (
    DashManifestMissingAdaptationSetError,
    DashManifestMissingPeriodError,
    DashManifestMissingRepresentationError,
    DashManifestNoDownloadLinksError,
    DashManifestParseError,
    DashManifestUnsupportedStructureError,
)
from core.utils.iso import parse_iso_8601_duration
from domain.media.protocols import StreamResolverProtocol
from domain.media.supported_media_types import SupportedStreamTypes
from domain.media.value_objects import MediaDownloadableLink, ResolvedMediaStream
from infrastructure.media.resolvers.dash_contexts import (
    DashManifestContext,
    DashSelectionContext,
)


class DashMPDResolver(StreamResolverProtocol):
    stream_type: SupportedStreamTypes = SupportedStreamTypes.DASH

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            headers={
                "User-Agent": config.media_http_user_agent,
                "Accept": config.media_http_accept_dash,
            },
            follow_redirects=config.media_http_follow_redirects,
            timeout=config.media_http_timeout_seconds,
        )
        self._is_client_owned = client is None

    async def can_resolve(self, stream_url: str) -> bool:
        if stream_url.lower().endswith(".mpd"):
            return True

        extension = Path(urlparse(stream_url).path).suffix.lower()
        if extension and extension != ".mpd":
            return False

        try:
            response = await self._client.get(stream_url)
            response.raise_for_status()
        except httpx.HTTPError:
            return False

        return "<MPD" in response.text

    async def resolve_stream(self, video_to_resolve: str) -> ResolvedMediaStream:
        response = await self._client.get(video_to_resolve)
        response.raise_for_status()

        manifest = self._build_manifest_context(video_to_resolve, response.text)
        selection = self._build_selection_context(manifest)
        downloadable_links = self._build_downloadable_links(selection)

        if not downloadable_links:
            raise DashManifestNoDownloadLinksError(manifest.manifest_url)

        return ResolvedMediaStream(
            source_url=video_to_resolve,
            stream_type=self.stream_type,
            links=downloadable_links,
            is_chunked=len(downloadable_links) > 1,
        )

    async def close(self) -> None:
        if self._is_client_owned:
            await self._client.aclose()

    def _build_manifest_context(
        self,
        manifest_url: str,
        payload: str,
    ) -> DashManifestContext:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as parse_error:
            raise DashManifestParseError(
                manifest_url=manifest_url,
                parse_error=str(parse_error),
            ) from parse_error

        namespace = self._extract_namespace(root.tag)
        return DashManifestContext(
            manifest_url=manifest_url,
            root=root,
            namespace=namespace,
        )

    def _extract_namespace(self, tag: str) -> str:
        if tag.startswith("{") and "}" in tag:
            return tag[1 : tag.index("}")]

        return ""

    def _build_selection_context(
        self, manifest: DashManifestContext
    ) -> DashSelectionContext:
        period = self._get_period(manifest)
        adaptation_set = self._get_adaptation_set(manifest, period)
        representation = self._get_representation(manifest, adaptation_set)
        segment_list, segment_template = self._get_segment_sources(
            manifest,
            adaptation_set,
            representation,
        )

        if segment_list is None and segment_template is None:
            raise DashManifestUnsupportedStructureError(
                manifest_url=manifest.manifest_url,
                reason="No SegmentList or SegmentTemplate found.",
            )

        representation_id = representation.attrib.get("id", "")
        bandwidth = self._to_int(representation.attrib.get("bandwidth", "0"), default=0)

        return DashSelectionContext(
            manifest=manifest,
            period=period,
            adaptation_set=adaptation_set,
            representation=representation,
            segment_list=segment_list,
            segment_template=segment_template,
            base_url=self._resolve_base_url(manifest, adaptation_set, representation),
            representation_base_url=self._read_child_text(
                manifest, representation, "BaseURL"
            ),
            representation_id=representation_id,
            bandwidth=bandwidth,
        )

    def _get_period(self, manifest: DashManifestContext) -> ET.Element:
        period = manifest.root.find(manifest.ns_tag("Period"))
        if period is None:
            raise DashManifestMissingPeriodError(manifest.manifest_url)

        return period

    def _get_adaptation_set(
        self,
        manifest: DashManifestContext,
        period: ET.Element,
    ) -> ET.Element:
        adaptation_sets = period.findall(manifest.ns_tag("AdaptationSet"))
        if not adaptation_sets:
            raise DashManifestMissingAdaptationSetError(manifest.manifest_url)

        for adaptation_set in adaptation_sets:
            mime_type = adaptation_set.attrib.get("mimeType", "")
            content_type = adaptation_set.attrib.get("contentType", "")
            if "video" in mime_type or content_type == "video":
                return adaptation_set

        return adaptation_sets[0]

    def _get_representation(
        self,
        manifest: DashManifestContext,
        adaptation_set: ET.Element,
    ) -> ET.Element:
        representations = adaptation_set.findall(manifest.ns_tag("Representation"))
        if not representations:
            raise DashManifestMissingRepresentationError(manifest.manifest_url)

        return max(
            representations,
            key=lambda element: self._to_int(
                element.attrib.get("bandwidth", "0"), default=0
            ),
        )

    def _get_segment_sources(
        self,
        manifest: DashManifestContext,
        adaptation_set: ET.Element,
        representation: ET.Element,
    ) -> tuple[ET.Element | None, ET.Element | None]:
        segment_list = representation.find(manifest.ns_tag("SegmentList"))
        segment_template = representation.find(manifest.ns_tag("SegmentTemplate"))

        if segment_list is None and segment_template is None:
            segment_list = adaptation_set.find(manifest.ns_tag("SegmentList"))
            segment_template = adaptation_set.find(manifest.ns_tag("SegmentTemplate"))

        return segment_list, segment_template

    def _resolve_base_url(
        self,
        manifest: DashManifestContext,
        adaptation_set: ET.Element,
        representation: ET.Element,
    ) -> str:
        base_url = manifest.manifest_url

        root_base = self._read_child_text(manifest, manifest.root, "BaseURL")
        if root_base:
            base_url = urljoin(base_url, root_base)

        adaptation_base = self._read_child_text(manifest, adaptation_set, "BaseURL")
        if adaptation_base:
            base_url = urljoin(base_url, adaptation_base)

        representation_base = self._read_child_text(manifest, representation, "BaseURL")
        if representation_base:
            base_url = urljoin(base_url, representation_base)

        return base_url

    def _read_child_text(
        self,
        manifest: DashManifestContext,
        node: ET.Element,
        child_name: str,
    ) -> str | None:
        child = node.find(manifest.ns_tag(child_name))
        if child is None or child.text is None:
            return None

        text = child.text.strip()
        return text or None

    def _build_downloadable_links(
        self,
        selection: DashSelectionContext,
    ) -> list[MediaDownloadableLink]:
        if self._should_use_single_representation_file(selection):
            return [self._single_file_link(selection)]

        if selection.segment_list is not None:
            links = self._parse_segment_list(selection)
        else:
            links = self._parse_segment_template(selection)

        if links:
            return links

        if self._has_representation_file(selection):
            return [self._single_file_link(selection)]

        return []

    def _parse_segment_list(
        self,
        selection: DashSelectionContext,
    ) -> list[MediaDownloadableLink]:
        segment_list = selection.segment_list
        if segment_list is None:
            return []

        links: list[MediaDownloadableLink] = []
        initialization = segment_list.find(selection.manifest.ns_tag("Initialization"))
        if initialization is not None:
            source_url = initialization.attrib.get("sourceURL")
            if source_url:
                links.append(
                    MediaDownloadableLink(
                        url=urljoin(selection.base_url, source_url),
                        sequence_number=0,
                        is_initialization_segment=True,
                    )
                )

        segment_urls = segment_list.findall(selection.manifest.ns_tag("SegmentURL"))
        for segment_index, segment_url in enumerate(segment_urls, start=1):
            media = segment_url.attrib.get("media")
            if not media:
                continue

            links.append(
                MediaDownloadableLink(
                    url=urljoin(selection.base_url, media),
                    sequence_number=segment_index,
                    is_initialization_segment=False,
                )
            )

        return self._replace_template_tokens(selection, links)

    def _parse_segment_template(
        self,
        selection: DashSelectionContext,
    ) -> list[MediaDownloadableLink]:
        segment_template = selection.segment_template
        if segment_template is None:
            return []

        media_template = segment_template.attrib.get("media")
        if media_template is None:
            return []

        links: list[MediaDownloadableLink] = []

        initialization_template = segment_template.attrib.get("initialization")
        if initialization_template:
            links.append(
                MediaDownloadableLink(
                    url=urljoin(selection.base_url, initialization_template),
                    sequence_number=0,
                    is_initialization_segment=True,
                )
            )

        start_number = self._to_int(
            segment_template.attrib.get("startNumber", "1"), default=1
        )
        segment_count = self._infer_segment_count(selection)

        for current_number in range(start_number, start_number + segment_count):
            expanded_url = self._expand_template(
                media_template, selection, current_number
            )
            links.append(
                MediaDownloadableLink(
                    url=urljoin(selection.base_url, expanded_url),
                    sequence_number=current_number,
                    is_initialization_segment=False,
                )
            )

        return links

    def _infer_segment_count(
        self,
        selection: DashSelectionContext,
    ) -> int:
        segment_template = selection.segment_template
        if segment_template is None:
            return 1

        timeline = segment_template.find(selection.manifest.ns_tag("SegmentTimeline"))
        if timeline is not None:
            timeline_segments = timeline.findall(selection.manifest.ns_tag("S"))
            total_segments = 0
            for segment in timeline_segments:
                repeat_count = self._to_int(segment.attrib.get("r", "0"), default=0)
                total_segments += repeat_count + 1

            return max(total_segments, 1)

        duration = self._to_int(segment_template.attrib.get("duration"), default=0)
        timescale = self._to_int(
            segment_template.attrib.get("timescale", "1"), default=1
        )
        presentation_duration = selection.manifest.root.attrib.get(
            "mediaPresentationDuration"
        )

        if duration <= 0 or timescale <= 0 or presentation_duration is None:
            return 1

        total_duration_seconds = parse_iso_8601_duration(presentation_duration)
        segment_duration_seconds = duration / timescale
        if segment_duration_seconds <= 0:
            return 1

        return max(int(math.ceil(total_duration_seconds / segment_duration_seconds)), 1)

    def _replace_template_tokens(
        self,
        selection: DashSelectionContext,
        links: list[MediaDownloadableLink],
    ) -> list[MediaDownloadableLink]:
        output: list[MediaDownloadableLink] = []
        for link in links:
            replaced_url = link.url.replace(
                "$RepresentationID$", selection.representation_id
            ).replace("$Bandwidth$", str(selection.bandwidth))
            output.append(
                MediaDownloadableLink(
                    url=replaced_url,
                    size_in_bytes=link.size_in_bytes,
                    sequence_number=link.sequence_number,
                    is_initialization_segment=link.is_initialization_segment,
                )
            )

        return output

    def _expand_template(
        self,
        template: str,
        selection: DashSelectionContext,
        number: int,
    ) -> str:
        value = template
        value = value.replace("$RepresentationID$", selection.representation_id)
        value = value.replace("$Bandwidth$", str(selection.bandwidth))
        value = value.replace("$Number$", str(number))
        return value

    def _should_use_single_representation_file(
        self,
        selection: DashSelectionContext,
    ) -> bool:
        if selection.segment_list is None:
            return False

        if not self._has_representation_file(selection):
            return False

        segment_urls = selection.segment_list.findall(
            selection.manifest.ns_tag("SegmentURL")
        )
        if not segment_urls:
            return True

        return all(
            segment.attrib.get("media") is None
            and ("mediaRange" in segment.attrib or "indexRange" in segment.attrib)
            for segment in segment_urls
        )

    def _has_representation_file(self, selection: DashSelectionContext) -> bool:
        representation_base_url = selection.representation_base_url
        if representation_base_url is None:
            return False

        if representation_base_url.endswith("/"):
            return False

        parsed = urlparse(representation_base_url)
        if parsed.scheme or parsed.netloc:
            return True

        return bool(Path(representation_base_url).name)

    def _single_file_link(
        self, selection: DashSelectionContext
    ) -> MediaDownloadableLink:
        return MediaDownloadableLink(
            url=selection.base_url,
            sequence_number=0,
            is_initialization_segment=False,
        )

    def _to_int(self, value: str | None, default: int) -> int:
        if value is None:
            return default

        if value.isdigit():
            return int(value)

        return default
