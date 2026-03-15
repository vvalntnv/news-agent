from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from core.errors.article_related import RawNewsDataAlreadyExistsError
from domain.news.entities import Article
from domain.news.repository_models.article import (
    ArticleRepositoryFilters,
    ArticleRepositoryUpdatePayload,
)
from infrastructure.database.models.article.repository import TortoiseArticleRepository

pytestmark = pytest.mark.anyio


async def test_create_delegates_to_raw_and_media_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                "source_url": "https://example.com/article",
            }
        ],
        "timestamp": "05/02/2026, 10:00:00",
        "author": "Author",
        "source_url": "https://example.com/article",
    }

    article = Article.model_validate(article_payload)

    saved_article = await repository.create(article)

    assert saved_article == article
    ensure_raw.assert_awaited_once_with(article)
    create_entry.assert_awaited_once_with(article, raw_data)
    ensure_media.assert_awaited_once_with(article, article_entry)


async def test_get_by_url_builds_domain_type(monkeypatch: pytest.MonkeyPatch) -> None:
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
            source_url="https://example.com/article",
            local_url="/tmp/video.mp4",
        ),
        SimpleNamespace(
            media_type="audio",
            source_url="https://example.com/article",
            local_url=None,
        ),
    ]

    article_entry = SimpleNamespace(
        id=123,
        raw_data=raw_data,
        article_url="https://example.com/article",
        media_items=media_rows,
    )

    get_article = AsyncMock(return_value=article_entry)
    monkeypatch.setattr(repository, "_get_article_entry_by_filters", get_article)

    loaded_article = await repository.get_by_url("https://example.com/article")

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
    assert media_values[0].source_url == "https://example.com/article"
    assert media_values[1].media_type.value == "audio"
    assert media_values[1].local_url is None


async def test_update_media_local_url_skips_model_queries_for_empty_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = TortoiseArticleRepository()

    article_filter = Mock(
        side_effect=AssertionError("ArticleEntry.filter should not run")
    )
    media_filter = Mock(
        side_effect=AssertionError("ArticleMedia.filter should not run")
    )

    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.ArticleEntry",
        SimpleNamespace(filter=article_filter),
    )
    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.ArticleMedia",
        SimpleNamespace(filter=media_filter),
    )

    await repository.update_media_local_url(
        "", "https://example.com/video.mp4", "/tmp/movie.mp4"
    )
    await repository.update_media_local_url(
        "https://example.com/article",
        "",
        "/tmp/movie.mp4",
    )

    article_filter.assert_not_called()
    media_filter.assert_not_called()


async def test_update_media_local_url_returns_when_media_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = TortoiseArticleRepository()

    article_entry = SimpleNamespace(id=123)
    article_first = AsyncMock(return_value=article_entry)
    article_filter = Mock(return_value=SimpleNamespace(first=article_first))

    media_first = AsyncMock(return_value=None)
    media_filter = Mock(return_value=SimpleNamespace(first=media_first))

    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.ArticleEntry",
        SimpleNamespace(filter=article_filter),
    )
    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.ArticleMedia",
        SimpleNamespace(filter=media_filter),
    )

    await repository.update_media_local_url(
        "https://example.com/article",
        "https://example.com/video.mp4",
        "/tmp/movie.mp4",
    )

    article_filter.assert_called_once_with(article_url="https://example.com/article")
    article_first.assert_awaited_once()
    media_filter.assert_called_once_with(
        article=article_entry,
        source_url="https://example.com/video.mp4",
    )
    media_first.assert_awaited_once()


async def test_update_media_local_url_updates_and_saves_media_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = TortoiseArticleRepository()

    article_entry = SimpleNamespace(id=321)
    article_first = AsyncMock(return_value=article_entry)
    article_filter = Mock(return_value=SimpleNamespace(first=article_first))

    media_row = SimpleNamespace(local_url="/tmp/old.mp4", save=AsyncMock())
    media_first = AsyncMock(return_value=media_row)
    media_filter = Mock(return_value=SimpleNamespace(first=media_first))

    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.ArticleEntry",
        SimpleNamespace(filter=article_filter),
    )
    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.ArticleMedia",
        SimpleNamespace(filter=media_filter),
    )

    await repository.update_media_local_url(
        "https://example.com/article",
        "https://example.com/video.mp4",
        "/tmp/new.mp4",
    )

    assert media_row.local_url == "/tmp/new.mp4"
    media_row.save.assert_awaited_once()


async def test_get_delegates_with_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = TortoiseArticleRepository()

    get_article = AsyncMock(return_value=None)
    monkeypatch.setattr(repository, "_get_article_entry_by_filters", get_article)

    filters = ArticleRepositoryFilters(article_url="https://example.com/article")
    loaded_article = await repository.get(filters)

    assert loaded_article is None
    get_article.assert_awaited_once_with(filters)


async def test_update_many_returns_updated_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = TortoiseArticleRepository()

    article_entry_a = SimpleNamespace(raw_data=SimpleNamespace())
    article_entry_b = SimpleNamespace(raw_data=SimpleNamespace())
    get_entries = AsyncMock(return_value=[article_entry_a, article_entry_b])
    apply_updates = AsyncMock()

    monkeypatch.setattr(repository, "_get_article_entries_by_filters", get_entries)
    monkeypatch.setattr(repository, "_apply_article_updates", apply_updates)

    filters = ArticleRepositoryFilters()
    payload = ArticleRepositoryUpdatePayload(title="updated-title")

    updated_count = await repository.update_many(filters, payload)

    assert updated_count == 2
    get_entries.assert_awaited_once_with(filters)
    assert apply_updates.await_count == 2


async def test_create_raw_article_data_raises_custom_error_for_duplicate_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = TortoiseArticleRepository()

    class _FakeQuery:
        async def first(self) -> object:
            return object()

    class _FakeRawNewsData:
        @staticmethod
        def filter(**_: object) -> _FakeQuery:
            return _FakeQuery()

    monkeypatch.setattr(
        "infrastructure.database.models.article.repository.RawNewsData",
        _FakeRawNewsData,
    )

    article = Article.model_validate(
        {
            "title": "title",
            "content": {"raw_content": "<p>content</p>", "quotes": []},
            "media": [],
            "timestamp": "2026-03-15T10:00:00Z",
            "author": "author",
            "source_url": "https://example.com/news",
        }
    )

    with pytest.raises(RawNewsDataAlreadyExistsError) as raised_error:
        await repository._create_raw_article_data(article)

    assert raised_error.value.internal_payload.code == "raw_news_data_already_exists"
