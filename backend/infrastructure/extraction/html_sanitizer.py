from typing import Literal

from bs4 import BeautifulSoup, Tag

type RootOfAnalysis = Literal["head", "body", "article"]

DEFAULT_IRRELEVANT_TAGS: tuple[str, ...] = (
    "audio",
    "canvas",
    "embed",
    "iframe",
    "noscript",
    "object",
    "script",
    "source",
    "style",
    "svg",
    "template",
    "track",
    "video",
)


class HtmlSanitizer:
    def __init__(
        self,
        attrs_to_retain: tuple[str, ...] | list[str] = ("href",),
        irrelevant_tags: tuple[str, ...] = DEFAULT_IRRELEVANT_TAGS,
    ) -> None:
        self.attrs_to_retain: set[str] = {
            attribute_name.lower() for attribute_name in attrs_to_retain
        }
        self.irrelevant_tags = irrelevant_tags

    def sanitize_html(
        self,
        html: str,
        *,
        root_of_analysis: RootOfAnalysis | None = None,
        selectors_to_remove: list[str] | None = None,
    ) -> str:
        soup = BeautifulSoup(html, "html.parser")
        analysis_root = self._resolve_analysis_root(soup, root_of_analysis)

        self._strip_irrelevant_tags(analysis_root, selectors_to_remove)
        self._retain_allowed_attributes(analysis_root)

        return str(analysis_root)

    def _resolve_analysis_root(
        self,
        soup: BeautifulSoup,
        root_of_analysis: RootOfAnalysis | None,
    ) -> Tag | BeautifulSoup:
        if root_of_analysis is None:
            return soup

        root_tag = soup.find(root_of_analysis)
        if root_tag is None:
            return soup

        return root_tag

    def _strip_irrelevant_tags(
        self,
        analysis_root: Tag | BeautifulSoup,
        selectors_to_remove: list[str] | None,
    ) -> None:
        for tag_name in self.irrelevant_tags:
            for tag in analysis_root.find_all(tag_name):
                tag.decompose()

        if selectors_to_remove is None:
            return

        for selector in selectors_to_remove:
            for tag in analysis_root.select(selector):
                tag.decompose()

    def _retain_allowed_attributes(self, analysis_root: Tag | BeautifulSoup) -> None:
        tags_to_process = analysis_root.find_all(True)

        if isinstance(analysis_root, Tag):
            tags_to_process = [analysis_root, *tags_to_process]

        for tag in tags_to_process:
            retained_attributes: dict[str, str | list[str]] = {}
            for attribute_name, attribute_value in tag.attrs.items():
                if attribute_name.lower() in self.attrs_to_retain:
                    retained_attributes[attribute_name] = attribute_value
            tag.attrs = retained_attributes  # type: ignore[assignment]
