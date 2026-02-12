from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
import httpx
from core.errors import MissingArticleContentError
from domain.news.entities import NewsItem, Article
from domain.news.protocols import ContentExtractor, Host
from domain.news.value_objects import ScrapeInformation, ArticleContent


class HtmlExtractor(ContentExtractor):
    """
    Extracts content from HTML pages.
    """

    def __init__(
        self,
        registered_scrapers: list[ScrapeInformation],
        attrs_to_retain: tuple[str, ...] | list[str] = ("href",),
    ) -> None:
        self.scraping_informations: dict[Host, ScrapeInformation] = {
            info.get_host(): info for info in registered_scrapers
        }
        self.attrs_to_retain: set[str] = {
            attribute.lower() for attribute in attrs_to_retain
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
        article_content = self._extract_article(relevant_scraping_info, soup)

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
            content=article_content,
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
    ) -> ArticleContent:
        article_container = soup.select_one(
            relevant_scraping_info.main_article_container
        )

        if article_container is None:
            raise MissingArticleContentError(
                scraping_url=relevant_scraping_info.scraping_url,
                selector=relevant_scraping_info.main_article_container,
            )

        article_container_copy = BeautifulSoup(str(article_container), "html.parser")
        container_root = article_container_copy.find()

        if container_root is None:
            raise MissingArticleContentError(
                scraping_url=relevant_scraping_info.scraping_url,
                selector=relevant_scraping_info.main_article_container,
            )

        self._strip_irrelevant_tags(
            container_root,
            relevant_scraping_info.video_containers,
        )
        quotes = self._extract_quotes(container_root)
        self._retain_allowed_attributes(container_root)

        return ArticleContent(
            raw_content=str(container_root),
            quotes=quotes,
        )

    def _strip_irrelevant_tags(
        self,
        article_container: Tag,
        video_selectors: list[str] | None,
    ) -> None:
        irrelevant_tags = (
            "audio",
            "canvas",
            "embed",
            "iframe",
            "noscript",
            "object",
            "script",
            "source",
            "style",
            "svg",
            "template",
            "track",
            "video",
        )

        for tag_name in irrelevant_tags:
            for tag in article_container.find_all(tag_name):
                tag.decompose()

        if video_selectors:
            for selector in video_selectors:
                for tag in article_container.select(selector):
                    tag.decompose()

    def _extract_quotes(self, article_container: Tag) -> list[str]:
        found_quotes: set[str] = set()

        for quote_tag_name in ("blockquote", "q"):
            for quote_tag in article_container.find_all(quote_tag_name):
                quote_text = quote_tag.get_text(" ", strip=True)

                if quote_text:
                    found_quotes.add(quote_text)

        return sorted(found_quotes)

    def _retain_allowed_attributes(self, article_container: Tag) -> None:
        tags_to_process = [article_container, *article_container.find_all(True)]
        for tag in tags_to_process:
            retained_attributes: dict[str, object] = {}
            for attribute_name, attribute_value in tag.attrs.items():
                if attribute_name.lower() in self.attrs_to_retain:
                    retained_attributes[attribute_name] = attribute_value
            tag.attrs = retained_attributes

    def _extract_videos_from_page(
        self,
        soup: BeautifulSoup,
        video_selectors: list[str],
    ) -> list[str]:
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
