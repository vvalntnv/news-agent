from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import httpx
from domain.news.entities import NewsItem, Article
from domain.news.protocols import ContentExtractor, Host
from domain.news.value_objects import ScrapeInformation


class HtmlExtractor(ContentExtractor):
    """
    Extracts content from HTML pages.
    """

    def __init__(self, registered_scrapers: list[ScrapeInformation]) -> None:
        self.scraping_informations: dict[Host, ScrapeInformation] = {
            info.get_host(): info for info in registered_scrapers
        }
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    async def extract(self, item: NewsItem) -> Article:
        relevant_scraping_info = self._get_relevant_scraper(item)

        page_response = await self.client.get(item.url)
        page_data = page_response.content

        soup = BeautifulSoup(page_data, "html.parser")
        article_text = self._extract_article(relevant_scraping_info, soup)

        # TODO: Decide if we REALLY want to traverse time containers (for now no)
        timestamp = soup.select_one(relevant_scraping_info.timestamps_conteiners[0])
        author_container = soup.select_one(relevant_scraping_info.author_container)

        if author_container is None:
            raise Exception(
                "There is no available article content for this news"
            )  # TODO: Create custom error

        videos = None
        if video_selectors := relevant_scraping_info.video_containers:
            videos = self._extract_videos_from_page(soup, video_selectors)

        return Article(
            title=item.title,
            content=article_text,
            videos=videos or [],
            author=author_container.get_text(),
            timestamp=(
                timestamp.get_text()
                if timestamp
                else datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            ),
            source_url=item.url,
        )

    def _extract_article(
        self,
        relevant_scraping_info: ScrapeInformation,
        soup: BeautifulSoup,
    ) -> str:
        article_container = soup.select_one(
            relevant_scraping_info.main_article_container
        )

        if article_container is None:
            raise Exception(
                "There is no available article content for this news"
            )  # TODO: Create custom error

        return article_container.get_text()

    def _extract_videos_from_page(self, soup, video_selectors: list[str]):
        videos: list[str] = []
        for video_selector in video_selectors:
            videos_containers = soup.select(video_selector)

            for container in videos_containers:
                video_link = container.get("href")
                does_video_exist = video_link is not None
                is_tag_link = isinstance(video_link, str)

                if does_video_exist and is_tag_link:
                    videos.append(video_link)

        return videos

    def _get_relevant_scraper(self, item: NewsItem) -> ScrapeInformation:
        url_info = urlparse(item.url)
        host = url_info.hostname

        assert host is not None, "Url Host is None, that should NEVER be possible"

        relevant_scraping_info = self.scraping_informations.get(host)

        if relevant_scraping_info is None:
            raise Exception(
                "No relevant scraper found for this news website"
            )  # TODO: Create custom errors

        return relevant_scraping_info
