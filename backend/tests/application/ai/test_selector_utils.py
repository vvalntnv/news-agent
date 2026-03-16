import pytest
from bs4 import BeautifulSoup

from application.ai.workflow.predefined.news_site_exploration.selector_utils import (
    is_main_selector_candidate_valid,
    looks_like_generic_tag_chain,
)
from core.config import config


def test_generic_chain_detection_flags_plain_tag_chain() -> None:
    is_generic_chain = looks_like_generic_tag_chain("main article section")

    assert is_generic_chain


def test_generic_chain_detection_respects_known_safe_chains() -> None:
    is_generic_chain = looks_like_generic_tag_chain(
        "main article",
        known_safe_generic_chains={"main article"},
    )

    assert not is_generic_chain


def test_generic_chain_detection_ignores_anchored_selector() -> None:
    is_generic_chain = looks_like_generic_tag_chain("main article.content")

    assert not is_generic_chain


def test_main_selector_candidate_validation_uses_config_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 40)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 2)

    soup = BeautifulSoup(
        """
        <html><body>
            <article itemprop='articleBody'>
                <p>Paragraph one with enough text.</p>
                <p>Paragraph two with enough text.</p>
            </article>
        </body></html>
        """,
        "html.parser",
    )

    is_valid = is_main_selector_candidate_valid(
        soup=soup,
        selector="article[itemprop='articleBody']",
    )

    assert is_valid


def test_main_selector_candidate_validation_rejects_multiple_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 1)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 1)

    soup = BeautifulSoup(
        """
        <html><body>
            <article><p>one</p></article>
            <article><p>two</p></article>
        </body></html>
        """,
        "html.parser",
    )

    is_valid = is_main_selector_candidate_valid(soup=soup, selector="article")

    assert not is_valid
