from dataclasses import dataclass

from bs4 import BeautifulSoup

from domain.news.value_objects import ScrapeInformation
from infrastructure.extraction.media_extraction_strategies.helpers.attribute_helpers import (
    get_string_from_tag_attribute,
)
from infrastructure.extraction.media_extraction_strategies.helpers.media_type_helpers import (
    determine_source_media_type,
)
from infrastructure.extraction.media_extraction_strategies.protocol import (
    AddMediaCallback,
    MediaExtractionStrategy,
)


@dataclass(frozen=True)
class SourceTagMediaCollectionStrategy(MediaExtractionStrategy):
    def collect(
        self,
        *,
        soup: BeautifulSoup,
        scrape_information: ScrapeInformation,
        add_media_callback: AddMediaCallback,
    ) -> None:
        del scrape_information
        for source_tag in soup.find_all("source"):
            media_type = determine_source_media_type(source_tag)
            if media_type is None:
                continue
            add_media_callback(
                get_string_from_tag_attribute(
                    tag=source_tag,
                    attribute_name="src",
                ),
                media_type,
            )
