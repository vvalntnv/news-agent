from typing import List
import httpx
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from database.models import RawNewsData
from news_sourcing.models import News, ScrapeInformation
from .protocols import NewsExtractor, NewsSource


class ScraperNewsSource(NewsSource, NewsExtractor):
    """
    Abstract Base Class for HTML Scraper-based news sources.
    """

    def __init__(self, base_url: str, registered_scrapers: list[ScrapeInformation]):
        self.scraping_informations: dict[str, ScrapeInformation] = {}
        self.source_link = base_url
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=30.0,
        )

        for scraper in registered_scrapers:
            url_data = urlparse(scraper.scraping_url)
            hostname = url_data.hostname

            assert hostname is not None, "no hostname provided for scraping"

            self.scraping_informations.update({hostname: scraper})

    async def check_for_news(self) -> List[News]:
        """
        Must implement logic to go to the main page and find news links.
        """
        out: list[News] = []
        for scraper_info in self.scraping_informations.values():
            news = await self._scrape_feed(scraper_info)
            out.extend(news)

        return out

    async def extract_news_data(self) -> list[RawNewsData]: ...

    async def close(self):
        await self.client.aclose()

    async def _scrape_feed(self, scraper_info: ScrapeInformation) -> list[News]:
        page = await self.client.get(scraper_info.scraping_url)
        soup = BeautifulSoup(page.content, "html.parser")

        news_containers = self._get_news_containers_elements(soup, scraper_info)

        explored_urls = set()
        out: list[News] = []
        for container in news_containers:
            news_tags = container.find_all(href=True)

            for tag in news_tags:
                url, title = self._get_url_and_title_from_tag(tag, scraper_info)
                if url in explored_urls:
                    continue

                out.append(News(link=url, title=title))

        return out

    def _get_url_and_title_from_tag(
        self,
        tag: Tag,
        scraper_info: ScrapeInformation,
    ) -> tuple[str, str | None]:
        def get_relative_link_from(tag: Tag):
            relative_link = tag["href"]
            assert isinstance(relative_link, str)

            full_url = urljoin(scraper_info.scraping_url, relative_link)
            return full_url

        def get_title_from(tag: Tag):
            breakpoint()
            title_selectors = ", ".join(scraper_info.titles_containers)
            title = tag.select_one(title_selectors)

            return title.get_text(strip=True) if title else None

        return (get_relative_link_from(tag), get_title_from(tag))

    def _get_news_containers_elements(
        self,
        soup: BeautifulSoup,
        scraper_info: ScrapeInformation,
    ):
        containers_distinctions = scraper_info.article_containers

        output_tags: list[Tag] = []
        for distinction in containers_distinctions:
            tags = soup.select(distinction)
            output_tags.extend(tags)

        return output_tags
