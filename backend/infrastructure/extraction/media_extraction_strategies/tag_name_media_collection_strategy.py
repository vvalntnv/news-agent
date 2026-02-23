from dataclasses import dataclass

from bs4 import BeautifulSoup

from domain.news.value_objects import MediaType, ScrapeInformation
from infrastructure.extraction.media_extraction_strategies.helpers.attribute_helpers import (
    get_string_from_tag_attribute,
)
from infrastructure.extraction.media_extraction_strategies.protocol import (
    AddMediaCallback,
    MediaExtractionStrategy,
)


@dataclass(frozen=True)
class TagNameMediaCollectionStrategy(MediaExtractionStrategy):
    tag_name: str
    attributes: tuple[str, ...]
    media_type: MediaType

    def collect(
        self,
        *,
        soup: BeautifulSoup,
        scrape_information: ScrapeInformation,
        add_media_callback: AddMediaCallback,
    ) -> None:
        del scrape_information
        for tag in soup.find_all(self.tag_name):
            for attribute_name in self.attributes:
                attribute_value = get_string_from_tag_attribute(
                    tag=tag,
                    attribute_name=attribute_name,
                )
                add_media_callback(attribute_value, self.media_type)
