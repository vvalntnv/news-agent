import re

import httpx
from bs4 import BeautifulSoup

from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationDependencies,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.prompts import (
    build_article_exploration_prompt,
)
from application.ai.workflow.step import WorkflowStep
from core.config import config
from domain.news.value_objects import ScrapeInformation


class ExploreArticlesStep(
    WorkflowStep[
        NewsSiteExplorationState,
        ScrapeInformation,
        NewsSiteExplorationDependencies,
    ]
):
    async def execute_logic(self) -> ScrapeInformation:
        partial_result = self.state.latest_result
        if partial_result is None:
            raise ValueError("Cannot explore articles without selectors")

        sample_article_urls = self.state.sample_article_urls
        if len(sample_article_urls) == 0:
            raise ValueError("Cannot explore articles without sampled article URLs")

        attempt_number = self.state.article_refinement_attempts + 1
        prompt = build_article_exploration_prompt(
            input_data=self.state.input_data,
            attempt_number=attempt_number,
            partial_result=partial_result,
            sample_article_urls=sample_article_urls,
            previous_validation_error=self.state.last_validation_error,
        )
        exploration_result = await self._run_exploration_with_agent(prompt=prompt)
        merged_result = self._merge_article_level_selectors(
            base_result=partial_result,
            refinement_result=exploration_result,
        )
        normalized_result = await self._normalize_article_level_selectors(
            result=merged_result,
            sample_article_urls=sample_article_urls,
        )
        self.state.article_refinement_attempts = attempt_number
        self.state.latest_result = normalized_result
        return normalized_result

    async def _run_exploration_with_agent(self, *, prompt: str) -> ScrapeInformation:
        max_agent_attempts = 3
        last_error: Exception | None = None

        for local_attempt in range(1, max_agent_attempts + 1):
            strict_prompt = (
                f"{prompt}\n\n"
                "OUTPUT CONTRACT: Return only a valid ScrapeInformation JSON object. "
                "No prose. No markdown. No analysis text."
            )
            try:
                run_result = await self.agent.run(strict_prompt)
                if not isinstance(run_result, ScrapeInformation):
                    raise TypeError(
                        "Expected ScrapeInformation result from workflow agent"
                    )

                return run_result
            except Exception as error:
                last_error = error
                has_remaining_attempts = local_attempt < max_agent_attempts
                if has_remaining_attempts:
                    continue

                raise

        assert last_error is not None
        raise last_error

    def _merge_article_level_selectors(
        self,
        *,
        base_result: ScrapeInformation,
        refinement_result: ScrapeInformation,
    ) -> ScrapeInformation:
        return base_result.model_copy(
            update={
                "main_article_container": refinement_result.main_article_container,
                "author_container": refinement_result.author_container,
                "image_containers": refinement_result.image_containers,
                "video_containers": refinement_result.video_containers,
                "audio_containers": refinement_result.audio_containers,
            }
        )

    async def _normalize_article_level_selectors(
        self,
        *,
        result: ScrapeInformation,
        sample_article_urls: list[str],
    ) -> ScrapeInformation:
        normalized_main_selector = result.main_article_container.strip()
        normalized_author_selector = result.author_container.strip()

        recovered_main_selector = await self._recover_stable_main_selector(
            sample_article_urls
        )
        if recovered_main_selector is not None:
            normalized_main_selector = recovered_main_selector

        if self._should_fallback_main_selector(normalized_main_selector):
            normalized_main_selector = result.main_article_container.strip()

        if self._should_fallback_author_selector(normalized_author_selector):
            normalized_author_selector = result.author_container.strip()

        return result.model_copy(
            update={
                "main_article_container": normalized_main_selector,
                "author_container": normalized_author_selector,
            }
        )

    def _should_fallback_main_selector(self, selector: str) -> bool:
        is_empty_selector = selector == ""
        if is_empty_selector:
            return True

        is_deep_selector = (
            selector.count(">") > config.workflow_selector_max_child_combinators
        )
        has_scope_pseudo = ":scope" in selector
        has_comma_union = "," in selector
        starts_with_generic_article = selector in {
            "article",
            "body article",
            "h1 + div",
        }
        is_generic_chain = self._looks_like_generic_chain(selector)
        ends_in_paragraph_target = selector.strip().endswith(
            "> p"
        ) or selector.strip().endswith(" p")

        return (
            is_deep_selector
            or has_scope_pseudo
            or has_comma_union
            or starts_with_generic_article
            or is_generic_chain
            or ends_in_paragraph_target
        )

    def _should_fallback_author_selector(self, selector: str) -> bool:
        is_empty_selector = selector == ""
        if is_empty_selector:
            return False

        has_positional_pseudo = any(
            token in selector
            for token in [":first", ":last", ":nth", ":only", "> div > div > div"]
        )
        return has_positional_pseudo

    def _looks_like_generic_chain(self, selector: str) -> bool:
        has_anchor_tokens = any(
            token in selector for token in [".", "#", "[", "data-", "itemprop", "role="]
        )
        if has_anchor_tokens:
            return False

        normalized_selector = selector.replace(">", " ")
        parts = [
            part.strip() for part in normalized_selector.split() if part.strip() != ""
        ]
        if len(parts) <= 1:
            return False

        plain_tag_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
        return all(plain_tag_pattern.match(part) is not None for part in parts)

    async def _recover_stable_main_selector(
        self,
        sample_article_urls: list[str],
    ) -> str | None:
        candidate_selectors = [
            "article[itemprop='articleBody']",
            "[itemprop='articleBody']",
            "main article",
            "[role='main'] article",
            "main",
            "[role='main']",
            "article",
            ".article-content",
            ".news-content",
            ".post-content",
        ]

        async with httpx.AsyncClient(
            headers={
                "User-Agent": config.media_http_user_agent,
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=config.media_http_follow_redirects,
            timeout=config.media_http_timeout_seconds,
        ) as client:
            soups: list[BeautifulSoup] = []
            for sample_url in sample_article_urls:
                try:
                    response = await client.get(sample_url)
                    response.raise_for_status()
                except Exception:
                    continue

                soups.append(BeautifulSoup(response.content, "html.parser"))

        if len(soups) == 0:
            return None

        for candidate_selector in candidate_selectors:
            is_valid_for_all = all(
                self._is_main_selector_candidate_valid(
                    soup=soup,
                    selector=candidate_selector,
                )
                for soup in soups
            )
            if is_valid_for_all:
                return candidate_selector

        return None

    def _is_main_selector_candidate_valid(
        self,
        *,
        soup: BeautifulSoup,
        selector: str,
    ) -> bool:
        matched_nodes = soup.select(selector)
        has_single_match = len(matched_nodes) == 1
        if not has_single_match:
            return False

        matched_node = matched_nodes[0]
        text_length = len(matched_node.get_text(" ", strip=True))
        has_enough_text = text_length >= config.workflow_main_selector_min_text_length
        if not has_enough_text:
            return False

        paragraph_count = len(matched_node.select("p"))
        has_enough_paragraphs = (
            paragraph_count >= config.workflow_main_selector_min_paragraph_count
        )
        if not has_enough_paragraphs:
            return False

        return True
