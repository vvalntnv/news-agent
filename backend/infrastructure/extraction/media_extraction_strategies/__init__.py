from infrastructure.extraction.media_extraction_strategies.protocol import (
    AddMediaCallback,
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

__all__ = [
    "AddMediaCallback",
    "MediaExtractionStrategy",
    "SelectorMediaCollectionStrategy",
    "SourceTagMediaCollectionStrategy",
    "TagNameMediaCollectionStrategy",
]
