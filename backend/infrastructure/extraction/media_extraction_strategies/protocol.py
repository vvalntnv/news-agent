from typing import Callable, Protocol

from bs4 import BeautifulSoup

from domain.news.value_objects import MediaType, ScrapeInformation

AddMediaCallback = Callable[[str | None, MediaType], None]


class MediaExtractionStrategy(Protocol):
    def collect(
        self,
        *,
        soup: BeautifulSoup,
        scrape_information: ScrapeInformation,
        add_media_callback: AddMediaCallback,
    ) -> None: ...
