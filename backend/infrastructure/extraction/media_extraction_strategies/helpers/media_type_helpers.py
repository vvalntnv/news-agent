from bs4 import Tag

from domain.news.value_objects import MediaType
from infrastructure.extraction.media_extraction_strategies.helpers.attribute_helpers import (
    get_string_from_tag_attribute,
)


def determine_source_media_type(source_tag: Tag) -> MediaType | None:
    type_attribute = get_string_from_tag_attribute(
        tag=source_tag,
        attribute_name="type",
    )
    media_type_from_mime = get_media_type_from_mime(type_attribute)
    parent = source_tag.parent

    if isinstance(parent, Tag):
        parent_name = parent.name.lower()

        if parent_name == "video":
            if media_type_from_mime == MediaType.AUDIO:
                return MediaType.AUDIO
            return MediaType.VIDEO

        if parent_name == "audio":
            return MediaType.AUDIO

        if parent_name == "picture":
            return MediaType.IMAGE

    return media_type_from_mime


def get_media_type_from_mime(mime_type: str | None) -> MediaType | None:
    if not mime_type:
        return None

    normalized = mime_type.split(";", 1)[0].strip().lower()

    if normalized.startswith("video/"):
        return MediaType.VIDEO

    if normalized.startswith("audio/"):
        return MediaType.AUDIO

    if normalized.startswith("image/"):
        return MediaType.IMAGE

    return None
