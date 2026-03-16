import pytest

from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.steps import (
    explore_articles_step as explore_articles_step_module,
)
from application.ai.workflow.predefined.news_site_exploration.steps.explore_articles_step import (
    ExploreArticlesStep,
)
from core.config import config
from domain.news.value_objects import ScrapeInformation

pytestmark = pytest.mark.anyio


class _FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _FakeClient:
    def __init__(self, pages_by_url: dict[str, bytes]) -> None:
        self._pages_by_url = pages_by_url

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = exc_type
        _ = exc
        _ = tb

    async def get(self, article_url: str) -> _FakeResponse:
        return _FakeResponse(self._pages_by_url[article_url])


def _build_state() -> NewsSiteExplorationState:
    input_data = NewsSiteExplorationInput(scraping_url="https://news.example")
    return NewsSiteExplorationState(
        input_data=input_data,
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
        sample_articles_count=input_data.sample_articles_count,
    )


def _build_result(
    *,
    main_selector: str,
    author_selector: str,
) -> ScrapeInformation:
    return ScrapeInformation(
        scrapingUrl="https://news.example",
        articleContainers=["article"],
        titlesContainers=["h2"],
        timestampsConteiners=["time"],
        summaryContainers=["p.summary"],
        imageContainers=None,
        videoContainers=None,
        audioContainers=None,
        mainArticleContainer=main_selector,
        authorContainer=author_selector,
    )


def _build_article_html(*, text: str, with_itemprop: bool = True) -> bytes:
    article_attributes = "itemprop='articleBody'" if with_itemprop else ""
    html = f"""
    <html><body>
      <main>
        <article {article_attributes}>
          <p>{text}</p>
          <p>{text}</p>
          <p>{text}</p>
        </article>
      </main>
    </body></html>
    """
    return html.encode("utf-8")


async def test_normalization_uses_recovered_stable_main_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step = ExploreArticlesStep(state=_build_state())
    result = _build_result(
        main_selector=" .original-main ",
        author_selector=".author",
    )

    async def _recover_stable(_sample_urls: list[str]) -> str | None:
        return "article[itemprop='articleBody']"

    monkeypatch.setattr(step, "_recover_stable_main_selector", _recover_stable)

    normalized = await step._normalize_article_level_selectors(
        result=result,
        sample_article_urls=["https://news.example/a"],
    )

    assert normalized.main_article_container == "article[itemprop='articleBody']"
    assert normalized.author_container == ".author"


async def test_normalization_falls_back_when_recovered_selector_is_generic_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step = ExploreArticlesStep(state=_build_state())
    result = _build_result(
        main_selector=" .original-main ",
        author_selector=".author",
    )

    async def _recover_generic_chain(_sample_urls: list[str]) -> str | None:
        return "main article section"

    monkeypatch.setattr(
        step,
        "_recover_stable_main_selector",
        _recover_generic_chain,
    )

    normalized = await step._normalize_article_level_selectors(
        result=result,
        sample_article_urls=["https://news.example/a"],
    )

    assert normalized.main_article_container == ".original-main"


def test_should_fallback_main_selector_flags_generic_tag_chain() -> None:
    step = ExploreArticlesStep(state=_build_state())

    should_fallback = step._should_fallback_main_selector("main article section")

    assert should_fallback


def test_should_fallback_author_selector_flags_positional_pattern() -> None:
    step = ExploreArticlesStep(state=_build_state())

    should_fallback = step._should_fallback_author_selector(".author :nth-child(2)")

    assert should_fallback


async def test_recover_stable_main_selector_finds_shared_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 40)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 2)

    pages = {
        "https://news.example/a": _build_article_html(text="Story one body text."),
        "https://news.example/b": _build_article_html(text="Story two body text."),
    }
    monkeypatch.setattr(
        explore_articles_step_module,
        "build_article_http_client",
        lambda: _FakeClient(pages),
    )

    step = ExploreArticlesStep(state=_build_state())
    recovered_selector = await step._recover_stable_main_selector(
        ["https://news.example/a", "https://news.example/b"]
    )

    assert recovered_selector == "article[itemprop='articleBody']"


async def test_recover_stable_main_selector_returns_none_without_valid_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 500)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 4)

    pages = {
        "https://news.example/a": _build_article_html(
            text="short text",
            with_itemprop=False,
        ),
        "https://news.example/b": b"<html><body><div>plain</div></body></html>",
    }
    monkeypatch.setattr(
        explore_articles_step_module,
        "build_article_http_client",
        lambda: _FakeClient(pages),
    )

    step = ExploreArticlesStep(state=_build_state())
    recovered_selector = await step._recover_stable_main_selector(
        ["https://news.example/a", "https://news.example/b"]
    )

    assert recovered_selector is None
