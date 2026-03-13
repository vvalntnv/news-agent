from __future__ import annotations

import pytest

from domain.news.repository_models.article import (
    ArticleRepositoryFilters,
    ArticleRepositoryUpdatePayload,
)
from domain.news.repositories.protocols import ArticleRepositoryProtocol
from domain.news.value_objects import Media, MediaType
from infrastructure.database.models.article.model import Article as ArticleEntry
from infrastructure.database.models.media.model import ArticleMedia
from infrastructure.database.models.raw_news_data.model import RawNewsData
from tests.utils.factories import ArticleFactory

pytestmark = pytest.mark.anyio


async def test_create_article_persists_raw_article_and_media(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    source_url = article_factory.create_article_source_url()
    video_media = article_factory.create_media_payload(
        media_type=MediaType.VIDEO,
        local_url=None,
    )
    image_media = article_factory.create_media_payload(
        media_type=MediaType.IMAGE,
        local_url="/static/media/image.jpg",
    )
    article = article_factory.create_article(
        article_url=source_url,
        quotes=["q1", "q2"],
        media=[video_media, image_media],
    )

    await article_repository.create(article)

    raw_row = await RawNewsData.get(url=source_url)
    article_row = await ArticleEntry.get(article_url=source_url)
    media_rows = await ArticleMedia.filter(article=article_row).all()

    assert raw_row.title == article.title
    assert raw_row.raw_text == article.content.raw_content
    assert raw_row.quotes == article.content.quotes
    assert raw_row.author == article.author
    assert raw_row.timestamp == article.timestamp
    assert article_row.raw_data_id == raw_row.id  # type: ignore
    assert len(media_rows) == 2


async def test_retrieve_article_returns_full_aggregate(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    source_url = article_factory.create_article_source_url()
    audio_media = article_factory.create_media_payload(
        media_type=MediaType.AUDIO,
        local_url=None,
    )
    article = article_factory.create_article(
        article_url=source_url,
        title="stored",
        author="stored-author",
        quotes=["quote-a"],
        media=[audio_media],
    )
    await article_repository.create(article)

    retrieved = await article_repository.get_by_url(source_url)

    assert retrieved is not None
    assert retrieved.title == "stored"
    assert retrieved.author == "stored-author"
    assert retrieved.content.quotes == ["quote-a"]
    assert len(retrieved.media) == 1
    assert retrieved.media[0].media_type.value == "audio"


async def test_article_exists_changes_after_create(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    source_url = article_factory.create_article_source_url()

    assert await article_repository.exists_by_url(source_url) is False

    await article_repository.create(
        article_factory.create_article(article_url=source_url)
    )

    assert await article_repository.exists_by_url(source_url) is True


async def test_update_article_updates_raw_and_media(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    source_url = article_factory.create_article_source_url()
    initial_video_media = article_factory.create_media_payload(
        media_type=MediaType.VIDEO,
        local_url=None,
    )
    initial = article_factory.create_article(
        article_url=source_url,
        title="old-title",
        author="old-author",
        quotes=["old-quote"],
        media=[initial_video_media],
    )
    await article_repository.create(initial)

    updated_video_media = article_factory.create_media_payload(
        source_url=initial_video_media["source_url"],
        media_type=MediaType.VIDEO,
        local_url="/static/media/video.mp4",
    )

    updated_image_media = article_factory.create_media_payload(
        media_type=MediaType.IMAGE,
        local_url=None,
    )
    update_payload = ArticleRepositoryUpdatePayload(
        title="new-title",
        author="new-author",
        quotes=["new-quote"],
        media=[
            Media.model_validate(updated_video_media),
            Media.model_validate(updated_image_media),
        ],
    )

    updated = await article_repository.update_one(
        ArticleRepositoryFilters(article_url=source_url),
        update_payload,
    )

    assert updated is not None
    raw_row = await RawNewsData.get(url=source_url)
    article_row = await ArticleEntry.get(article_url=source_url)
    video_row = await ArticleMedia.get(
        article=article_row,
        media_type="video",
    )
    image_row = await ArticleMedia.get(
        article=article_row,
        media_type="image",
    )

    assert raw_row.title == "new-title"
    assert raw_row.author == "new-author"
    assert raw_row.quotes == ["new-quote"]
    assert video_row.local_url == "/static/media/video.mp4"
    assert image_row.local_url is None


async def test_update_article_media_local_url_updates_existing_media(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    article_url = article_factory.create_article_source_url()
    video_media = article_factory.create_media_payload(
        media_type=MediaType.VIDEO,
        local_url=None,
    )
    await article_repository.create(
        article_factory.create_article(
            article_url=article_url,
            media=[video_media],
        )
    )

    await article_repository.update_media_local_url(
        article_url,
        str(video_media["source_url"]),
        "/static/media/movie.mp4",
    )

    article_row = await ArticleEntry.get(article_url=article_url)
    media_row = await ArticleMedia.get(article=article_row, media_type="video")
    assert media_row.local_url == "/static/media/movie.mp4"


async def test_retrieve_article_returns_none_for_unknown_url(
    article_repository: ArticleRepositoryProtocol,
) -> None:
    retrieved = await article_repository.get_by_url("https://example.com/unknown")
    assert retrieved is None


async def test_create_many_and_get_many_round_trip(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    first_article = article_factory.create_article()
    second_article = article_factory.create_article()

    created_articles = await article_repository.create_many(
        [first_article, second_article]
    )

    assert len(created_articles) == 2

    loaded_articles = await article_repository.get_many(
        ArticleRepositoryFilters(),
        order_by=("id",),
    )

    assert len(loaded_articles) >= 2


async def test_update_many_updates_multiple_articles(
    article_repository: ArticleRepositoryProtocol,
    article_factory: ArticleFactory,
) -> None:
    first_article = article_factory.create_article(author="old-author")
    second_article = article_factory.create_article(author="old-author")
    await article_repository.create_many([first_article, second_article])

    updated_count = await article_repository.update_many(
        ArticleRepositoryFilters(),
        ArticleRepositoryUpdatePayload(author="new-author"),
    )

    assert updated_count >= 2

    loaded_articles = await article_repository.get_many(ArticleRepositoryFilters())
    assert len(loaded_articles) >= 2
    assert all(article.author == "new-author" for article in loaded_articles)
