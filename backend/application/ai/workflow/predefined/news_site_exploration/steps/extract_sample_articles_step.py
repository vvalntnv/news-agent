from typing import Iterable

from bs4 import BeautifulSoup

from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.selector_utils import (
    STABLE_MAIN_SELECTOR_CANDIDATES,
    USABLE_MAIN_SELECTOR_CANDIDATES,
    build_article_http_client,
    has_selector_match_with_minimum_content,
    is_main_selector_candidate_valid,
)
from application.ai.workflow.step import WorkflowStep
from domain.news.value_objects import ScrapeInformation
from infrastructure.sources.web_scraper_source import WebScraperSource


class ExtractSampleArticlesStep(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    async def execute_logic(self) -> ScrapeInformation:
        latest_result = self.state.latest_result
        if latest_result is None:
            raise ValueError("Cannot extract sample articles without selectors")

        source = WebScraperSource(
            base_url=self.state.scraping_url,
            registered_scrapers=[latest_result],
        )
        try:
            all_articles = await source.check_for_news()
        finally:
            await source.close()

        article_urls = [article.url for article in all_articles]
        if len(article_urls) == 0:
            raise ValueError("No articles discovered with the provided selectors")

        max_sample_size = min(len(article_urls), self.state.sample_articles_count)
        self.state.sample_article_urls = await self._select_structured_article_urls(
            article_urls=article_urls,
            sample_size=max_sample_size,
        )
        return latest_result

    async def _select_structured_article_urls(
        self,
        *,
        article_urls: list[str],
        sample_size: int,
    ) -> list[str]:
        page_contents: dict[str, bytes] = {}
        selected_urls: list[str] = []

        async with build_article_http_client() as client:
            for article_url in article_urls:
                if len(selected_urls) >= sample_size:
                    break

                page = await client.get(article_url)
                page_content = page.content
                is_structured = self._is_structured_article_page(
                    page_content=page_content
                )
                if not is_structured:
                    continue

                page_contents[article_url] = page_content
                shared_selector = self._recover_stable_main_selector(
                    page_contents.values()
                )
                has_shared_selector = shared_selector is not None

                if has_shared_selector:
                    selected_urls.append(article_url)

        has_enough_selected = len(selected_urls) >= sample_size
        if has_enough_selected:
            return selected_urls

        if len(selected_urls) == 0:
            fallback_count = min(len(article_urls), sample_size)
            return article_urls[:fallback_count]

        return selected_urls

    def _is_structured_article_page(
        self,
        *,
        page_content: bytes | str,
    ) -> bool:
        soup = BeautifulSoup(page_content, "html.parser")
        has_article_tag = soup.select_one("article") is not None
        has_main_tag = soup.select_one("main") is not None
        paragraph_count = len(soup.select("p"))
        has_paragraphs = paragraph_count >= 3
        has_usable_main_candidate = self._has_usable_main_candidate(soup)

        return (
            has_article_tag or has_main_tag or has_paragraphs
        ) and has_usable_main_candidate

    def _has_usable_main_candidate(self, soup: BeautifulSoup) -> bool:
        for selector in USABLE_MAIN_SELECTOR_CANDIDATES:
            has_match = has_selector_match_with_minimum_content(
                soup=soup,
                selector=selector,
                min_text_length=120,
                min_paragraph_count=2,
            )
            if has_match:
                return True

        return False

    def _recover_stable_main_selector(
        self,
        page_contents: Iterable[bytes],
    ) -> str | None:
        soups = [BeautifulSoup(content, "html.parser") for content in page_contents]

        if len(soups) == 0:
            return None

        for candidate_selector in STABLE_MAIN_SELECTOR_CANDIDATES:
            is_valid_for_all = all(
                is_main_selector_candidate_valid(
                    soup=soup,
                    selector=candidate_selector,
                )
                for soup in soups
            )
            if is_valid_for_all:
                return candidate_selector

        return None
