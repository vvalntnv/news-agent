from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from core.errors import (
    MissingArticleContentError,
    MissingAuthorError,
    NoScraperFoundError,
)
from domain.news.entities import Article, NewsItem
from domain.news.protocols import ContentExtractor, Host
from domain.news.value_objects import (
    ArticleContent,
    Media,
    MediaType,
    ScrapeInformation,
)
from infrastructure.extraction.media_extraction_strategies import (
    MediaExtractionStrategy,
)

from infrastructure.extraction.media_extraction_strategies.helpers.strategy_execution_plan_helpers import (
    create_default_comperhensive_media_collection_strategy_execution_plan,
)


class HtmlExtractor(ContentExtractor):
    """
    Extracts content from HTML pages.
    """

    def __init__(
        self,
        registered_scrapers: list[ScrapeInformation],
        attrs_to_retain: tuple[str, ...] | list[str] = ("href",),
        media_collection_strategy_execution_plan: (
            tuple[MediaExtractionStrategy, ...] | None
        ) = None,
    ) -> None:
        self.scraping_informations: dict[Host, ScrapeInformation] = {
            info.get_host(): info for info in registered_scrapers
        }
        self.attrs_to_retain: set[str] = {
            attribute.lower() for attribute in attrs_to_retain
        }
        self.media_collection_strategy_execution_plan = (
            media_collection_strategy_execution_plan
            or create_default_comprehensive_media_collection_strategy_execution_plan()
        )
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
            raise MissingAuthorError(
                scraping_url=relevant_scraping_info.scraping_url,
                selector=relevant_scraping_info.author_container,
            )

        media_items = self._extract_media(
            soup,
            relevant_scraping_info,
            base_url=item.url,
        )

        return Article(
            title=item.title,
            content=article_content,
            media=media_items,
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
            self._gather_media_selectors(relevant_scraping_info),
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
        selectors: list[str] | None,
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

        if selectors:
            for selector in selectors:
                for tag in article_container.select(selector):
                    tag.decompose()

    def _extract_quotes(self, article_container: Tag) -> list[str]:
        found_quotes: set[str] = set()

        for quote_tag_name in ("blockquote", "q"):
            for quote_tag in article_container.find_all(quote_tag_name):
                quote_text = quote_tag.get_text(" ", strip=True)

                if quote_text:
                    found_quotes.add(quote_text)

        return list(found_quotes)

    def _retain_allowed_attributes(self, article_container: Tag) -> None:
        tags_to_process = [article_container, *article_container.find_all(True)]
        for tag in tags_to_process:
            retained_attributes: dict[str, str | list[str]] = {}
            for attribute_name, attribute_value in tag.attrs.items():
                if attribute_name.lower() in self.attrs_to_retain:
                    retained_attributes[attribute_name] = attribute_value
            tag.attrs = retained_attributes  # type: ignore[assignment]

    def _gather_media_selectors(
        self, relevant_scraping_info: ScrapeInformation
    ) -> list[str] | None:
        selectors: list[str] = []
        for group in (
            relevant_scraping_info.image_containers,
            relevant_scraping_info.video_containers,
            relevant_scraping_info.audio_containers,
        ):
            if group:
                selectors.extend(group)

        return selectors or None

    def _extract_media(
        self,
        soup: BeautifulSoup,
        relevant_scraping_info: ScrapeInformation,
        base_url: str,
    ) -> list[Media]:
        seen_urls: set[str] = set()
        media_items: list[Media] = []

        def register_normalized_media(
            url_value: str | None, media_type: MediaType
        ) -> None:
            normalized_url = self._normalize_media_url(url_value, base_url)
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                media_items.append(
                    Media(
                        media_type=media_type,
                        article_url=normalized_url,
                        local_url=None,
                    )
                )

        for media_collection_strategy in self.media_collection_strategy_execution_plan:
            media_collection_strategy.collect(
                soup=soup,
                scrape_information=relevant_scraping_info,
                add_media_callback=register_normalized_media,
            )

        return media_items

    def _normalize_media_url(self, candidate: str | None, base_url: str) -> str | None:
        if not candidate or not isinstance(candidate, str):
            return None

        cleaned_candidate = candidate.strip()
        if not cleaned_candidate:
            return None

        joined = urljoin(base_url, cleaned_candidate)
        parsed = urlparse(joined)
        normalized = parsed._replace(fragment="").geturl()

        return normalized

    def _get_relevant_scraper(self, item: NewsItem) -> ScrapeInformation:
        url_info = urlparse(item.url)
        host = url_info.hostname

        assert host is not None, "Url Host is None, that should NEVER be possible"

        relevant_scraping_info = self.scraping_informations.get(host)

        if relevant_scraping_info is None:
            raise NoScraperFoundError(url=item.url, host=host)

        return relevant_scraping_info
