import pytest

from application.ai.workflow.predefined.news_site_exploration.models import (
    NewsSiteExplorationInput,
    NewsSiteExplorationState,
)
from application.ai.workflow.predefined.news_site_exploration.steps import (
    extract_sample_articles_step as extract_sample_articles_step_module,
)
from application.ai.workflow.predefined.news_site_exploration.steps.extract_sample_articles_step import (
    ExtractSampleArticlesStep,
)
from core.config import config
from domain.news.value_objects import ScrapeInformation

pytestmark = pytest.mark.anyio


class _FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content


class _FakeClient:
    def __init__(self, page_by_url: dict[str, bytes]) -> None:
        self._page_by_url = page_by_url

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = exc_type
        _ = exc
        _ = tb

    async def get(self, article_url: str) -> _FakeResponse:
        page_content = self._page_by_url[article_url]
        return _FakeResponse(page_content)


def _build_step() -> ExtractSampleArticlesStep:
    input_data = NewsSiteExplorationInput(scraping_url="https://news.example")
    state = NewsSiteExplorationState(
        input_data=input_data,
        scraping_url=input_data.scraping_url,
        max_attempts=input_data.max_attempts,
        sample_articles_count=input_data.sample_articles_count,
        latest_result=_build_result(),
    )
    return ExtractSampleArticlesStep(state=state)


def _build_result() -> ScrapeInformation:
    return ScrapeInformation(
        scrapingUrl="https://news.example",
        articleContainers=["article"],
        titlesContainers=["h2"],
        timestampsConteiners=["time"],
        summaryContainers=["p.summary"],
        imageContainers=None,
        videoContainers=None,
        audioContainers=None,
        mainArticleContainer="article",
        authorContainer=".author",
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


async def test_select_structured_article_urls_prefers_structured_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 40)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 2)

    article_urls = [
        "https://news.example/a",
        "https://news.example/b",
        "https://news.example/c",
    ]
    fake_pages = {
        "https://news.example/a": _build_article_html(text="A stable story body."),
        "https://news.example/b": _build_article_html(
            text="Another stable story body."
        ),
        "https://news.example/c": b"<html><body><div>noise</div></body></html>",
    }

    monkeypatch.setattr(
        extract_sample_articles_step_module,
        "build_article_http_client",
        lambda: _FakeClient(fake_pages),
    )

    step = _build_step()
    selected_urls = await step._select_structured_article_urls(
        article_urls=article_urls,
        sample_size=2,
    )

    assert selected_urls == ["https://news.example/a", "https://news.example/b"]


async def test_select_structured_article_urls_falls_back_when_no_structured_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    article_urls = [
        "https://news.example/a",
        "https://news.example/b",
        "https://news.example/c",
    ]
    fake_pages = {
        url: b"<html><body><div>not structured</div></body></html>"
        for url in article_urls
    }

    monkeypatch.setattr(
        extract_sample_articles_step_module,
        "build_article_http_client",
        lambda: _FakeClient(fake_pages),
    )

    step = _build_step()
    selected_urls = await step._select_structured_article_urls(
        article_urls=article_urls,
        sample_size=2,
    )

    assert selected_urls == ["https://news.example/a", "https://news.example/b"]


def test_recover_stable_main_selector_returns_none_for_empty_input() -> None:
    step = _build_step()

    selector = step._recover_stable_main_selector([])

    assert selector is None


def test_recover_stable_main_selector_finds_itemprop_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "workflow_main_selector_min_text_length", 40)
    monkeypatch.setattr(config, "workflow_main_selector_min_paragraph_count", 2)
    step = _build_step()
    pages = [
        _build_article_html(text="Primary story body on page one."),
        _build_article_html(text="Primary story body on page two."),
    ]

    selector = step._recover_stable_main_selector(pages)

    assert selector == "article[itemprop='articleBody']"
