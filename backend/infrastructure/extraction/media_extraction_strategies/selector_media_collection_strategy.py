from dataclasses import dataclass
from typing import Callable

from bs4 import BeautifulSoup

from domain.news.value_objects import MediaType, ScrapeInformation
from infrastructure.extraction.media_extraction_strategies.helpers.attribute_helpers import (
    get_string_from_tag_attribute,
)
from infrastructure.extraction.media_extraction_strategies.protocol import (
    AddMediaCallback,
    MediaExtractionStrategy,
)

SelectorResolver = Callable[[ScrapeInformation], list[str] | None]


@dataclass(frozen=True)
class SelectorMediaCollectionStrategy(MediaExtractionStrategy):
    selectors_resolver: SelectorResolver
    media_type: MediaType

    def collect(
        self,
        *,
        soup: BeautifulSoup,
        scrape_information: ScrapeInformation,
        add_media_callback: AddMediaCallback,
    ) -> None:
        selectors = self.selectors_resolver(scrape_information)
        if not selectors:
            return

        for selector in selectors:
            for element in soup.select(selector):
                add_media_callback(
                    get_string_from_tag_attribute(
                        tag=element,
                        attribute_name="href",
                    ),
                    self.media_type,
                )
                add_media_callback(
                    get_string_from_tag_attribute(
                        tag=element,
                        attribute_name="src",
                    ),
                    self.media_type,
                )
