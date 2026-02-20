from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from domain.news.entities import Article
from domain.news.value_objects import ArticleContent
from infrastructure.database.repositories import TortoiseArticleRepository


pytestmark = pytest.mark.anyio


class _FakeQuery:
    def __init__(self, result: object) -> None:
        self._result = result

    async def first(self) -> object:
        return self._result


async def test_save_maps_article_content_to_raw_news_data(monkeypatch: pytest.MonkeyPatch):
    repository = TortoiseArticleRepository()

    existing_row = SimpleNamespace(
        title="old-title",
        raw_text="old-content",
        quotes=[],
        videos=[],
        save=AsyncMock(),
    )

    def fake_filter(*_args: object, **_kwargs: object) -> _FakeQuery:
        return _FakeQuery(existing_row)

    monkeypatch.setattr(
        "infrastructure.database.repositories.RawNewsData.filter",
        fake_filter,
    )

    article = Article(
        title="new-title",
        content=ArticleContent(
            raw_content="<article><p>sanitized content</p></article>",
            quotes=["quoted text"],
        ),
        videos=["https://example.com/video.mp4"],
        timestamp="05/02/2026, 10:00:00",
        author="Author",
        source_url="https://example.com/article",
    )

    saved_article = await repository.save(article)

    assert saved_article == article
    assert existing_row.title == "new-title"
    assert existing_row.raw_text == "<article><p>sanitized content</p></article>"
    assert existing_row.quotes == ["quoted text"]
    assert existing_row.videos == ["https://example.com/video.mp4"]
    existing_row.save.assert_awaited_once()


async def test_get_by_url_reconstructs_article_content(monkeypatch: pytest.MonkeyPatch):
    repository = TortoiseArticleRepository()

    stored_row = SimpleNamespace(
        title="stored-title",
        raw_text="<article><p>stored content</p></article>",
        quotes=["quote one", 1, "quote two"],
        videos=["https://example.com/1.mp4", 2],
        url="https://example.com/article",
    )

    def fake_filter(*_args: object, **_kwargs: object) -> _FakeQuery:
        return _FakeQuery(stored_row)

    monkeypatch.setattr(
        "infrastructure.database.repositories.RawNewsData.filter",
        fake_filter,
    )

    loaded_article = await repository.get_by_url("https://example.com/article")

    assert loaded_article is not None
    assert loaded_article.content.raw_content == "<article><p>stored content</p></article>"
    assert loaded_article.content.quotes == ["quote one", "quote two"]
    assert loaded_article.videos == ["https://example.com/1.mp4"]
