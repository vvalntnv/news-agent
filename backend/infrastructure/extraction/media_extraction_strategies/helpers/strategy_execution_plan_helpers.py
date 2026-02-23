from domain.news.value_objects import MediaType, ScrapeInformation
from infrastructure.extraction.media_extraction_strategies.protocol import (
    MediaExtractionStrategy,
)
from infrastructure.extraction.media_extraction_strategies.selector_media_collection_strategy import (
    SelectorMediaCollectionStrategy,
)
from infrastructure.extraction.media_extraction_strategies.source_tag_media_collection_strategy import (
    SourceTagMediaCollectionStrategy,
)
from infrastructure.extraction.media_extraction_strategies.tag_name_media_collection_strategy import (
    TagNameMediaCollectionStrategy,
)


def _get_image_selectors(scrape_information: ScrapeInformation) -> list[str] | None:
    return scrape_information.image_containers


def _get_video_selectors(scrape_information: ScrapeInformation) -> list[str] | None:
    return scrape_information.video_containers


def _get_audio_selectors(scrape_information: ScrapeInformation) -> list[str] | None:
    return scrape_information.audio_containers


def create_default_comprehensive_media_collection_strategy_execution_plan() -> (
    tuple[MediaExtractionStrategy, ...]
):
    return (
        TagNameMediaCollectionStrategy(
            tag_name="img",
            attributes=("src", "data-src"),
            media_type=MediaType.IMAGE,
        ),
        TagNameMediaCollectionStrategy(
            tag_name="video",
            attributes=("src", "data-src"),
            media_type=MediaType.VIDEO,
        ),
        TagNameMediaCollectionStrategy(
            tag_name="audio",
            attributes=("src", "data-src"),
            media_type=MediaType.AUDIO,
        ),
        SourceTagMediaCollectionStrategy(),
        SelectorMediaCollectionStrategy(
            selectors_resolver=_get_image_selectors,
            media_type=MediaType.IMAGE,
        ),
        SelectorMediaCollectionStrategy(
            selectors_resolver=_get_video_selectors,
            media_type=MediaType.VIDEO,
        ),
        SelectorMediaCollectionStrategy(
            selectors_resolver=_get_audio_selectors,
            media_type=MediaType.AUDIO,
        ),
    )
