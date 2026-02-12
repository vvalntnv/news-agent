from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class DashManifestContext:
    manifest_url: str
    root: ET.Element
    namespace: str

    def ns_tag(self, tag_name: str) -> str:
        if not self.namespace:
            return tag_name

        return f"{{{self.namespace}}}{tag_name}"


@dataclass(frozen=True)
class DashSelectionContext:
    manifest: DashManifestContext
    period: ET.Element
    adaptation_set: ET.Element
    representation: ET.Element
    segment_list: ET.Element | None
    segment_template: ET.Element | None
    base_url: str
    representation_base_url: str | None
    representation_id: str
    bandwidth: int
