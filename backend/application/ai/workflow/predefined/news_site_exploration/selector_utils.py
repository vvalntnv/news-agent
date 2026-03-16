import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Tag

from core.config import config

ARTICLE_ITEMPROP_SELECTOR = "article[itemprop='articleBody']"
ITEMPROP_SELECTOR = "[itemprop='articleBody']"
MAIN_ARTICLE_SELECTOR = "main article"
ROLE_MAIN_ARTICLE_SELECTOR = "[role='main'] article"
MAIN_SELECTOR = "main"
ROLE_MAIN_SELECTOR = "[role='main']"
ARTICLE_SELECTOR = "article"
ARTICLE_CONTENT_SELECTOR = ".article-content"
NEWS_CONTENT_SELECTOR = ".news-content"
POST_CONTENT_SELECTOR = ".post-content"

STABLE_MAIN_SELECTOR_CANDIDATES: tuple[str, ...] = (
    ARTICLE_ITEMPROP_SELECTOR,
    ITEMPROP_SELECTOR,
    MAIN_ARTICLE_SELECTOR,
    ROLE_MAIN_ARTICLE_SELECTOR,
    MAIN_SELECTOR,
    ROLE_MAIN_SELECTOR,
    ARTICLE_SELECTOR,
    ARTICLE_CONTENT_SELECTOR,
    NEWS_CONTENT_SELECTOR,
    POST_CONTENT_SELECTOR,
)

USABLE_MAIN_SELECTOR_CANDIDATES: tuple[str, ...] = (
    ARTICLE_ITEMPROP_SELECTOR,
    ITEMPROP_SELECTOR,
    MAIN_ARTICLE_SELECTOR,
    ROLE_MAIN_ARTICLE_SELECTOR,
    ARTICLE_SELECTOR,
    MAIN_SELECTOR,
)


@dataclass(frozen=True)
class MainNodeContentStats:
    text_length: int
    paragraph_count: int


def build_article_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": config.media_http_user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
        follow_redirects=config.media_http_follow_redirects,
        timeout=config.media_http_timeout_seconds,
    )


def looks_like_generic_tag_chain(
    selector: str,
    *,
    known_safe_generic_chains: set[str] | frozenset[str] = frozenset(),
) -> bool:
    normalized_selector = selector.strip()
    if normalized_selector in known_safe_generic_chains:
        return False

    has_anchor_tokens = any(
        token in normalized_selector
        for token in [".", "#", "[", "data-", "itemprop", "role="]
    )
    if has_anchor_tokens:
        return False

    flattened_selector = normalized_selector.replace(">", " ")
    parts = [part.strip() for part in flattened_selector.split() if part.strip() != ""]
    if len(parts) <= 1:
        return False

    plain_tag_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    return all(plain_tag_pattern.match(part) is not None for part in parts)


def build_main_node_content_stats(main_node: Tag) -> MainNodeContentStats:
    text_content = main_node.get_text(" ", strip=True)
    text_length = len(text_content)
    paragraph_count = len(main_node.select("p"))
    return MainNodeContentStats(
        text_length=text_length,
        paragraph_count=paragraph_count,
    )


def has_selector_match_with_minimum_content(
    *,
    soup: BeautifulSoup,
    selector: str,
    min_text_length: int,
    min_paragraph_count: int,
) -> bool:
    matched_nodes = soup.select(selector)
    has_single_match = len(matched_nodes) == 1
    if not has_single_match:
        return False

    content_stats = build_main_node_content_stats(matched_nodes[0])
    has_enough_text = content_stats.text_length >= min_text_length
    has_enough_paragraphs = content_stats.paragraph_count >= min_paragraph_count
    return has_enough_text and has_enough_paragraphs


def is_main_selector_candidate_valid(*, soup: BeautifulSoup, selector: str) -> bool:
    return has_selector_match_with_minimum_content(
        soup=soup,
        selector=selector,
        min_text_length=config.workflow_main_selector_min_text_length,
        min_paragraph_count=config.workflow_main_selector_min_paragraph_count,
    )
