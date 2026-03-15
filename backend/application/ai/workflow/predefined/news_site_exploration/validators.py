import re

import httpx
from bs4 import BeautifulSoup, Tag

from core.config import config
from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationState,
)
from domain.news.value_objects import ScrapeInformation
from infrastructure.sources.web_scraper_source import WebScraperSource


async def validate_scrape_information(
    state: NewsSiteExplorationState,
    result: ScrapeInformation,
) -> None:
    _ = state
    is_result_valid = is_valid_scrape_information(result)
    if not is_result_valid:
        raise ValueError("ScrapeInformation is missing one or more required selectors")

    validate_selector_stability(result)
    await validate_selector_semantics_against_sample_articles(state, result)
    await validate_feed_selector_discovery(result)


def is_valid_scrape_information(result: ScrapeInformation) -> bool:
    has_article_selectors = len(result.article_containers) > 0
    has_title_selectors = len(result.titles_containers) > 0
    has_timestamp_selectors = len(result.timestamps_conteiners) > 0
    has_summary_selectors = len(result.summary_containers) > 0
    has_main_container = len(result.main_article_container.strip()) > 0
    has_author_container = len(result.author_container.strip()) > 0

    return (
        has_article_selectors
        and has_title_selectors
        and has_timestamp_selectors
        and has_summary_selectors
        and has_main_container
        and has_author_container
    )


def validate_selector_stability(result: ScrapeInformation) -> None:
    selectors_to_validate = {
        "main_article_container": result.main_article_container,
        "author_container": result.author_container,
    }

    for selector_name, selector_value in selectors_to_validate.items():
        normalized_selector = selector_value.strip()
        if normalized_selector == "":
            continue

        is_deep_selector = _is_deep_selector(normalized_selector)
        if is_deep_selector:
            raise ValueError(
                f"{selector_name} is too deep and brittle: '{normalized_selector}'"
            )

        uses_positional_pseudo = _uses_positional_pseudo(normalized_selector)
        if uses_positional_pseudo:
            raise ValueError(
                f"{selector_name} uses positional pseudo selectors: '{normalized_selector}'"
            )

        is_generic_chain = _is_generic_tag_chain(normalized_selector)
        if is_generic_chain:
            raise ValueError(
                f"{selector_name} is a generic tag chain and not stable: '{normalized_selector}'"
            )


async def validate_selector_semantics_against_sample_articles(
    state: NewsSiteExplorationState,
    result: ScrapeInformation,
) -> None:
    sample_article_urls = state.sample_article_urls
    if len(sample_article_urls) == 0:
        raise ValueError("No sample article URLs available for semantic validation")

    async with httpx.AsyncClient(
        headers={
            "User-Agent": config.media_http_user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
        follow_redirects=config.media_http_follow_redirects,
        timeout=config.media_http_timeout_seconds,
    ) as client:
        for sample_url in sample_article_urls:
            soup = await _fetch_article_soup(client=client, article_url=sample_url)
            _assert_main_selector_is_semantically_valid(
                soup=soup,
                selector=result.main_article_container,
                article_url=sample_url,
            )


async def validate_feed_selector_discovery(result: ScrapeInformation) -> None:
    source = WebScraperSource(
        base_url=result.scraping_url, registered_scrapers=[result]
    )
    try:
        discovered_news = await source.check_for_news()
    finally:
        await source.close()

    has_discovered_news = len(discovered_news) > 0
    if not has_discovered_news:
        raise ValueError(
            "Feed selectors are not usable because no news links were discovered "
            "with the current selector set."
        )


def _is_deep_selector(selector: str) -> bool:
    child_combinator_count = selector.count(">")
    max_allowed_combinators = config.workflow_selector_max_child_combinators
    return child_combinator_count > max_allowed_combinators


def _uses_positional_pseudo(selector: str) -> bool:
    should_disallow_positional_pseudo = (
        config.workflow_selector_disallow_positional_pseudo
    )
    if not should_disallow_positional_pseudo:
        return False

    positional_pseudo_pattern = r":(first|last|nth|only)-"
    return re.search(positional_pseudo_pattern, selector) is not None


def _is_generic_tag_chain(selector: str) -> bool:
    known_safe_generic_chains = {"main article"}
    if selector.strip() in known_safe_generic_chains:
        return False

    has_anchor_tokens = any(
        token in selector for token in [".", "#", "[", "data-", "itemprop", "role="]
    )
    if has_anchor_tokens:
        return False

    normalized_selector = selector.replace(">", " ")
    parts = [part.strip() for part in normalized_selector.split() if part.strip() != ""]
    if len(parts) <= 1:
        return False

    plain_tag_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    are_all_plain_tags = all(
        plain_tag_pattern.match(part) is not None for part in parts
    )
    return are_all_plain_tags


async def _fetch_article_soup(
    *,
    client: httpx.AsyncClient,
    article_url: str,
) -> BeautifulSoup:
    response = await client.get(article_url)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def _assert_main_selector_is_semantically_valid(
    *,
    soup: BeautifulSoup,
    selector: str,
    article_url: str,
) -> None:
    matched_nodes = soup.select(selector)
    matched_count = len(matched_nodes)
    has_exactly_one_match = matched_count == 1
    if not has_exactly_one_match:
        raise ValueError(
            "main_article_container must match exactly one element in each sample "
            f"article. url={article_url}, matches={matched_count}, selector='{selector}'"
        )

    main_node = matched_nodes[0]
    _assert_main_node_has_enough_content(main_node=main_node, article_url=article_url)
    _assert_main_node_is_not_link_heavy(main_node=main_node, article_url=article_url)


def _assert_main_node_has_enough_content(*, main_node: Tag, article_url: str) -> None:
    text_content = main_node.get_text(" ", strip=True)
    text_length = len(text_content)
    min_text_length = config.workflow_main_selector_min_text_length
    has_enough_text = text_length >= min_text_length
    if not has_enough_text:
        raise ValueError(
            "main_article_container has too little text content for article body "
            f"extraction. url={article_url}, text_length={text_length}"
        )

    paragraph_count = len(main_node.select("p"))
    min_paragraph_count = config.workflow_main_selector_min_paragraph_count
    has_enough_paragraphs = paragraph_count >= min_paragraph_count
    if not has_enough_paragraphs:
        raise ValueError(
            "main_article_container has too few paragraph elements. "
            f"url={article_url}, paragraph_count={paragraph_count}"
        )


def _assert_main_node_is_not_link_heavy(*, main_node: Tag, article_url: str) -> None:
    paragraph_nodes = main_node.select("p")
    paragraph_text_total_length = sum(
        len(paragraph.get_text(" ", strip=True)) for paragraph in paragraph_nodes
    )
    paragraph_link_text_total_length = sum(
        len(anchor.get_text(" ", strip=True))
        for paragraph in paragraph_nodes
        for anchor in paragraph.select("a[href]")
    )

    has_enough_paragraph_signal = paragraph_text_total_length > 0
    if has_enough_paragraph_signal:
        normalized_text_length = paragraph_text_total_length
        link_text_total_length = paragraph_link_text_total_length
    else:
        fallback_text_content = main_node.get_text(" ", strip=True)
        fallback_text_length = len(fallback_text_content)
        normalized_text_length = fallback_text_length if fallback_text_length > 0 else 1
        link_text_total_length = sum(
            len(anchor.get_text(" ", strip=True))
            for anchor in main_node.select("a[href]")
        )

    link_density_ratio = link_text_total_length / normalized_text_length
    max_link_density_ratio = config.workflow_main_selector_max_link_density_ratio

    is_link_density_too_high = link_density_ratio > max_link_density_ratio
    if is_link_density_too_high:
        raise ValueError(
            "main_article_container is too link-heavy and likely points to utility "
            "or navigation content. "
            f"url={article_url}, link_density={link_density_ratio:.2f}"
        )
