from typing import List
import httpx
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag

from domain.news.entities import NewsItem
from domain.news.protocols import NewsSource
from domain.news.value_objects import ScrapeInformation


class WebScraperSource(NewsSource):
    """
    HTML Scraper-based news source implementation.
    Finds links on a page based on CSS selectors.
    """

    def __init__(self, base_url: str, registered_scrapers: list[ScrapeInformation]):
        self.scraping_informations: list[ScrapeInformation] = registered_scrapers
        self.source_link = base_url
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    async def check_for_news(self) -> List[NewsItem]:
        """
        Go to the main page and find news links.
        """
        articles: dict[str, NewsItem] = {}

        for scraper_info in self.scraping_informations:
            news = await self._scrape_feed(scraper_info)
            for article in news:
                if article.url not in articles:
                    articles.update({article.url: article})
                else:
                    loaded_article = articles[article.url]
                    does_already_have_article_title = loaded_article.title is None
                    does_current_article_have_title = article.title is not None

                    if (
                        does_already_have_article_title
                        and does_current_article_have_title
                    ):
                        articles.update({article.url: article})

        return list(articles.values())

    async def close(self):
        await self.client.aclose()

    async def _scrape_feed(self, scraper_info: ScrapeInformation) -> list[NewsItem]:
        page = await self.client.get(scraper_info.scraping_url)
        soup = BeautifulSoup(page.content, "html.parser")

        news_containers = self._get_news_containers_elements(soup, scraper_info)

        out: list[NewsItem] = []
        for container in news_containers:
            news_tags = container.find_all(href=True)

            for tag in news_tags:
                url, title = self._get_url_and_title_from_tag(tag, scraper_info)
                out.append(NewsItem(url=url, title=title))

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
            title_selectors = ", ".join(scraper_info.titles_containers)
            tag_parent = tag.parent

            if tag_parent is None:
                text = tag.get_text()
                return text or None

            title = tag_parent.select_one(title_selectors)
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
