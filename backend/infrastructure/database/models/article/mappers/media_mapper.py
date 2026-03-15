from collections.abc import Iterable

from domain.news.value_objects import Media, MediaType
from infrastructure.database.models.media.model import ArticleMedia


def map_media_rows(media_rows: Iterable[ArticleMedia]) -> list[Media]:
    """Convert ORM media rows into domain media models."""

    mapped_media: list[Media] = []
    for media_row in media_rows:
        try:
            media_type = MediaType(media_row.media_type)
        except ValueError:
            continue

        mapped_media.append(
            Media(
                media_type=media_type,
                source_url=media_row.source_url,
                local_url=media_row.local_url,
            )
        )

    return mapped_media
