from collections.abc import Sequence
from typing import cast

from domain.news.entities import Article
from domain.news.repository_models.article import (
    ArticleRepositoryFilters,
    ArticleRepositoryUpdatePayload,
)
from domain.news.repositories.protocols import ArticleRepositoryProtocol
from domain.news.value_objects import ArticleContent
from infrastructure.database.models.article.mappers import article_mapper
from infrastructure.database.models.article.model import Article as ArticleEntry
from infrastructure.database.models.media.model import ArticleMedia
from infrastructure.database.models.raw_news_data.model import RawNewsData
from tortoise.queryset import QuerySet


class TortoiseArticleRepository(ArticleRepositoryProtocol):
    """Tortoise ORM implementation of article repository operations."""

    async def create(self, payload: Article) -> Article:
        raw_data = await self._create_raw_article_data(payload)
        article_entry = await self._create_article_record(payload, raw_data)
        await self._ensure_media_for_article(payload, article_entry)
        return payload

    async def create_many(self, payloads: Sequence[Article]) -> list[Article]:
        created_articles: list[Article] = []
        for payload in payloads:
            created_article = await self.create(payload)
            created_articles.append(created_article)
        return created_articles

    async def update_one(
        self,
        filters: ArticleRepositoryFilters,
        payload: ArticleRepositoryUpdatePayload,
    ) -> Article | None:
        article_entry = await self._get_article_entry_by_filters(filters)
        if article_entry is None:
            return None

        await self._apply_article_updates(article_entry, payload)
        await article_entry.fetch_related("raw_data", "media_items")
        return article_mapper.map_article_entry_to_domain(article_entry)

    async def update_many(
        self,
        filters: ArticleRepositoryFilters,
        payload: ArticleRepositoryUpdatePayload,
    ) -> int:
        article_entries = await self._get_article_entries_by_filters(filters)
        updated_rows = 0
        for article_entry in article_entries:
            await self._apply_article_updates(article_entry, payload)
            updated_rows += 1

        return updated_rows

    async def get(self, filters: ArticleRepositoryFilters) -> Article | None:
        article_entry = await self._get_article_entry_by_filters(filters)
        if article_entry is None:
            return None

        return article_mapper.map_article_entry_to_domain(article_entry)

    async def get_many(
        self,
        filters: ArticleRepositoryFilters,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: tuple[str, ...] = (),
    ) -> list[Article]:
        query = self._build_article_filters(ArticleEntry.all(), filters)

        if len(order_by) > 0:
            query = query.order_by(*order_by)

        if offset > 0:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        article_entries = await query.prefetch_related("raw_data", "media_items")

        mapped_articles: list[Article] = []
        for article_entry in article_entries:
            mapped_article = article_mapper.map_article_entry_to_domain(article_entry)
            if mapped_article is None:
                continue
            mapped_articles.append(mapped_article)

        return mapped_articles

    async def get_by_url(self, url: str) -> Article | None:
        if len(url) == 0:
            return None

        return await self.get(ArticleRepositoryFilters(article_url=url))

    async def exists_by_url(self, url: str) -> bool:
        article = await self.get_by_url(url)
        return article is not None

    async def update_media_local_url(
        self,
        article_url: str,
        source_url: str,
        local_url: str,
    ) -> None:
        if len(article_url) == 0 or len(source_url) == 0:
            return

        article_entry = await ArticleEntry.filter(article_url=article_url).first()
        if article_entry is None:
            return

        media_row = await ArticleMedia.filter(
            article=article_entry,
            source_url=source_url,
        ).first()

        if media_row is None:
            return

        if media_row.local_url == local_url:
            return

        media_row.local_url = local_url
        await media_row.save()

    async def _create_raw_article_data(self, article: Article) -> RawNewsData:
        existing_raw = await RawNewsData.filter(url=article.article_url).first()
        if existing_raw is not None:
            raise Exception(
                "RawNewsData with this url already exists. Cannot create a new one"
            )

        return await RawNewsData.create(
            title=article.title,
            raw_text=article.content.raw_content,
            quotes=article.content.quotes,
            url=article.article_url,
            author=article.author,
            timestamp=article.timestamp,
        )

    async def _create_article_record(
        self,
        article: Article,
        raw_data: RawNewsData,
    ) -> ArticleEntry:
        return await ArticleEntry.create(
            article_url=article.article_url or "",
            raw_data=raw_data,
        )

    async def _get_article_entry_by_filters(
        self,
        filters: ArticleRepositoryFilters,
    ) -> ArticleEntry | None:
        query = self._build_article_filters(ArticleEntry.all(), filters)
        article_entry = await query.first()
        if article_entry is None:
            return None

        await article_entry.fetch_related("raw_data", "media_items")
        return article_entry

    async def _get_article_entries_by_filters(
        self,
        filters: ArticleRepositoryFilters,
    ) -> list[ArticleEntry]:
        query = self._build_article_filters(ArticleEntry.all(), filters)
        return await query.prefetch_related("raw_data", "media_items")

    def _build_article_filters(
        self,
        query: QuerySet[ArticleEntry],
        filters: ArticleRepositoryFilters,
    ) -> QuerySet[ArticleEntry]:
        if filters.article_id is not None:
            query = query.filter(id=filters.article_id)

        if filters.article_url is not None:
            query = query.filter(article_url=filters.article_url)

        return query

    async def _apply_article_updates(
        self,
        article_entry: ArticleEntry,
        payload: ArticleRepositoryUpdatePayload,
    ) -> None:
        raw_data = article_entry.raw_data
        if raw_data is None:
            return

        if payload.title is not None:
            raw_data.title = payload.title

        if payload.raw_content is not None:
            raw_data.raw_text = payload.raw_content

        if payload.quotes is not None:
            raw_data.quotes = payload.quotes

        if payload.author is not None:
            raw_data.author = payload.author

        if payload.timestamp is not None:
            raw_data.timestamp = payload.timestamp

        if payload.article_url is not None:
            article_entry.article_url = payload.article_url

        await raw_data.save()
        await article_entry.save()

        if payload.media is None:
            return

        article_for_media = Article(
            article_id=article_entry.id,
            title=raw_data.title,
            content=ArticleContent(
                raw_content=raw_data.raw_text,
                quotes=raw_data.quotes,
            ),
            media=payload.media,
            timestamp=raw_data.timestamp,
            author=raw_data.author,
            article_url=article_entry.article_url,
        )
        await self._ensure_media_for_article(article_for_media, article_entry)

    async def _ensure_media_for_article(
        self,
        article: Article,
        article_entry: ArticleEntry,
    ) -> None:
        existing_media = await ArticleMedia.filter(article=article_entry).all()
        existing_lookup: dict[tuple[str, str], ArticleMedia] = {
            (media.media_type, media.source_url): media for media in existing_media
        }

        for media_item in article.media:
            media_type_value = media_item.media_type.value
            media_key = (media_type_value, media_item.source_url)
            stored_media = existing_lookup.get(media_key)

            if stored_media is None:
                await ArticleMedia.create(
                    article=article_entry,
                    media_type=media_type_value,
                    source_url=media_item.source_url,
                    local_url=media_item.local_url,
                )
                continue

            needs_update = (
                media_item.local_url is not None
                and stored_media.local_url != media_item.local_url
            )
            if needs_update:
                local_url_value = cast(str, media_item.local_url)
                stored_media.local_url = local_url_value
                await stored_media.save()
