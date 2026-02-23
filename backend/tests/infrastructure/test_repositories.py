from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from domain.news.entities import Article
from infrastructure.database.repositories import TortoiseArticleRepository

pytestmark = pytest.mark.anyio


class _FakeQuery:
    def __init__(self, result: object) -> None:
        self._result = result

    async def first(self) -> object:
        return self._result


async def test_create_article_delegates_to_raw_and_media_helpers(
    monkeypatch: pytest.MonkeyPatch,
):
    repository = TortoiseArticleRepository()

    raw_data = SimpleNamespace()
    article_entry = SimpleNamespace()

    ensure_raw = AsyncMock(return_value=raw_data)
    create_entry = AsyncMock(return_value=article_entry)
    ensure_media = AsyncMock()

    monkeypatch.setattr(repository, "_create_raw_article_data", ensure_raw)
    monkeypatch.setattr(repository, "_create_article_record", create_entry)
    monkeypatch.setattr(repository, "_ensure_media_for_article", ensure_media)

    article_payload = {
        "title": "new-title",
        "content": {
            "raw_content": "<article><p>sanitized content</p></article>",
            "quotes": ["quoted text"],
        },
        "media": [
            {
                "media_type": "video",
                "article_url": "https://example.com/article",
            }
        ],
        "timestamp": "05/02/2026, 10:00:00",
        "author": "Author",
        "source_url": "https://example.com/article",
    }

    article = Article.model_validate(article_payload)

    saved_article = await repository.create_article(article)

    assert saved_article == article
    ensure_raw.assert_awaited_once_with(article)
    create_entry.assert_awaited_once_with(article, raw_data)
    ensure_media.assert_awaited_once_with(article, article_entry)


async def test_retrieve_article_builds_domain_type(monkeypatch: pytest.MonkeyPatch):
    repository = TortoiseArticleRepository()

    raw_data = SimpleNamespace(
        title="stored-title",
        raw_text="<article><p>stored content</p></article>",
        quotes=["quote one", "quote two"],
        author="Stored Author",
        timestamp="2026-05-02T10:00:00Z",
    )

    media_rows = [
        SimpleNamespace(
            media_type="video",
            article_url="https://example.com/article",
            local_url="/tmp/video.mp4",
        ),
        SimpleNamespace(
            media_type="audio",
            article_url="https://example.com/article",
            local_url=None,
        ),
    ]

    article_entry = SimpleNamespace(
        raw_data=raw_data,
        article_url="https://example.com/article",
        media_items=media_rows,
    )

    get_article = AsyncMock(return_value=article_entry)
    monkeypatch.setattr(repository, "_get_article_by_url", get_article)

    loaded_article = await repository.retrieve_article("https://example.com/article")

    assert loaded_article is not None
    assert (
        loaded_article.content.raw_content == "<article><p>stored content</p></article>"
    )
    assert loaded_article.content.quotes == ["quote one", "quote two"]
    assert loaded_article.author == "Stored Author"
    assert loaded_article.timestamp == "2026-05-02T10:00:00Z"
    media_values = getattr(loaded_article, "media", [])
    assert len(media_values) == 2
    assert media_values[0].media_type.value == "video"
    assert media_values[0].article_url == "https://example.com/article"
    assert media_values[1].media_type.value == "audio"
    assert media_values[1].local_url is None


async def test_update_article_media_local_url_forwards(monkeypatch: pytest.MonkeyPatch):
    repository = TortoiseArticleRepository()

    updater = AsyncMock()
    monkeypatch.setattr(repository, "_update_media_local_url", updater)

    await repository.update_article_media_local_url(
        "https://example.com/article",
        "video",
        "/tmp/movie.mp4",
    )

    updater.assert_awaited_once_with(
        "https://example.com/article",
        "video",
        "/tmp/movie.mp4",
    )
