from __future__ import annotations

import pytest

from domain.news.value_objects import MediaType
from domain.news.protocols import ArticleRepository
from infrastructure.database.models.article.model import Article as ArticleEntry
from infrastructure.database.models.media.model import ArticleMedia
from infrastructure.database.models.raw_news_data.model import RawNewsData
from tests.utils.factories import ArticleFactory

pytestmark = pytest.mark.anyio


async def test_create_article_persists_raw_article_and_media(
    article_repository: ArticleRepository,
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

    await article_repository.create_article(article)

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
    article_repository: ArticleRepository,
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
    await article_repository.create_article(article)

    retrieved = await article_repository.retrieve_article(source_url)

    assert retrieved is not None
    assert retrieved.title == "stored"
    assert retrieved.author == "stored-author"
    assert retrieved.content.quotes == ["quote-a"]
    assert len(retrieved.media) == 1
    assert retrieved.media[0].media_type.value == "audio"


async def test_article_exists_changes_after_create(
    article_repository: ArticleRepository,
    article_factory: ArticleFactory,
) -> None:
    source_url = article_factory.create_article_source_url()

    assert await article_repository.article_exists(source_url) is False

    await article_repository.create_article(
        article_factory.create_article(article_url=source_url)
    )

    assert await article_repository.article_exists(source_url) is True


async def test_update_article_updates_raw_and_media(
    article_repository: ArticleRepository,
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
    await article_repository.create_article(initial)

    updated_video_media = article_factory.create_media_payload(
        source_url=initial_video_media["source_url"],
        media_type=MediaType.VIDEO,
        local_url="/static/media/video.mp4",
    )

    updated_image_media = article_factory.create_media_payload(
        media_type=MediaType.IMAGE,
        local_url=None,
    )
    updated = article_factory.create_article(
        article_url=source_url,
        title="new-title",
        author="new-author",
        quotes=["new-quote"],
        media=[updated_video_media, updated_image_media],
    )

    await article_repository.update_article(updated)

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
    article_repository: ArticleRepository,
    article_factory: ArticleFactory,
) -> None:
    article_url = article_factory.create_article_source_url()
    video_media = article_factory.create_media_payload(
        media_type=MediaType.VIDEO,
        local_url=None,
    )
    await article_repository.create_article(
        article_factory.create_article(
            article_url=article_url,
            media=[video_media],
        )
    )

    await article_repository.update_article_media_local_url(
        article_url,
        video_media["source_url"],
        "/static/media/movie.mp4",
    )

    article_row = await ArticleEntry.get(article_url=article_url)
    media_row = await ArticleMedia.get(article=article_row, media_type="video")
    assert media_row.local_url == "/static/media/movie.mp4"


async def test_retrieve_article_returns_none_for_unknown_url(
    article_repository: ArticleRepository,
) -> None:
    retrieved = await article_repository.retrieve_article("https://example.com/unknown")
    assert retrieved is None
