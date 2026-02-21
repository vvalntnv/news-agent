from typing import cast

from domain.news.entities import Article
from domain.news.protocols import ArticleRepository
from infrastructure.database.models.article.model import Article as ArticleEntry
from infrastructure.database.models.media.model import ArticleMedia
from infrastructure.database.models.raw_news_data.model import RawNewsData
from infrastructure.database.repositories.article.mappers import article_mapper


class TortoiseArticleRepository(ArticleRepository):
    """Tortoise ORM implementation of the ArticleRepository."""

    async def create_article(self, article: Article) -> Article:
        raw_data = await self._create_raw_article_data(article)
        article_entry = await self._create_article_record(article, raw_data)
        await self._ensure_media_for_article(article, article_entry)
        return article

    async def get_article_by_id(self, id: int) -> Article:
        article_entry = await ArticleEntry.get_or_none(id=id)
        if article_entry is None:
            raise Exception("No article with this id exists")  # TODO: External error

        article = article_mapper.map_article_entry_to_domain(article_entry)
        assert article is not None, "This should never happen"

        return article

    async def retrieve_article(self, url: str) -> Article | None:
        article_entry = await self._get_article_by_url(url)
        if article_entry is None or article_entry.raw_data is None:
            return None

        return article_mapper.map_article_entry_to_domain(article_entry)

    async def update_article(self, article: Article) -> Article:
        raw_data = await self._update_raw_article_data(article)
        article_entry = (
            await ArticleEntry.get_or_none(id=article.article_id)
            if article.article_id
            else await self._get_article_by_url(article.source_url or "")
        )

        if article_entry is None:
            article_entry = await self._create_article_record(article, raw_data)
        else:
            article_entry = await self._update_article_record(article_entry, article)

        await self._ensure_media_for_article(article, article_entry)
        return article

    async def update_article_media_local_url(
        self,
        article_url: str,
        media_type: str,
        local_url: str,
    ) -> None:
        await self._update_media_local_url(article_url, media_type, local_url)

    async def article_exists(self, url: str) -> bool:
        article_entry = await self._get_article_by_url(url)
        return article_entry is not None

    async def _update_raw_article_data(self, article: Article) -> RawNewsData:
        existing_raw = await RawNewsData.filter(url=article.source_url).first()
        if existing_raw is None:
            raise Exception(
                "RawNewsData does not exist"
            )  # TODO: Create custom external error

        existing_raw.title = article.title
        existing_raw.raw_text = article.content.raw_content
        existing_raw.quotes = article.content.quotes
        existing_raw.author = article.author
        existing_raw.timestamp = article.timestamp

        await existing_raw.save()
        return existing_raw

    async def _create_raw_article_data(self, article: Article) -> RawNewsData:
        existing_raw = await RawNewsData.filter(url=article.source_url).first()
        if existing_raw is not None:
            raise Exception(
                "RawNewsData with this url already exists. Cannot create a new one"
            )  # TODO: Create custom external error

        return await RawNewsData.create(
            title=article.title,
            raw_text=article.content.raw_content,
            quotes=article.content.quotes,
            url=article.source_url,
            author=article.author,
            timestamp=article.timestamp,
        )

    async def _create_article_record(
        self,
        article: Article,
        raw_data: RawNewsData,
    ) -> ArticleEntry:
        return await ArticleEntry.create(
            article_url=article.source_url or "",
            raw_data=raw_data,
        )

    async def _get_article_by_url(self, url: str) -> ArticleEntry | None:
        if not url:
            return None

        article_entry = await ArticleEntry.filter(article_url=url).first()
        if article_entry is None:
            return None

        await article_entry.fetch_related("raw_data", "media_items")
        return article_entry

    async def _update_article_record(
        self,
        article_entry: ArticleEntry,
        article: Article,
    ) -> ArticleEntry:
        if article.source_url:
            article_entry.article_url = article.source_url

        await article_entry.save()
        return article_entry

    async def _ensure_media_for_article(
        self,
        article: Article,
        article_entry: ArticleEntry,
    ) -> None:
        existing_media = await ArticleMedia.filter(article=article_entry).all()
        existing_lookup: dict[tuple[str, str], ArticleMedia] = {
            (media.media_type, media.article_url): media for media in existing_media
        }

        for media_item in article.media:
            media_type_value = media_item.media_type.value
            media_key = (media_type_value, media_item.article_url)
            stored_media = existing_lookup.get(media_key)

            if stored_media is None:
                await ArticleMedia.create(
                    article=article_entry,
                    media_type=media_type_value,
                    article_url=media_item.article_url,
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

    async def _update_media_local_url(
        self,
        article_url: str,
        media_type: str,
        local_url: str,
    ) -> None:
        if not article_url:
            return

        article_entry = await ArticleEntry.filter(article_url=article_url).first()
        if article_entry is None:
            return

        media_row = await ArticleMedia.filter(
            article=article_entry,
            media_type=media_type,
        ).first()

        if media_row is None:
            await ArticleMedia.create(
                article=article_entry,
                media_type=media_type,
                article_url=article_url,
                local_url=local_url,
            )
            return

        if media_row.local_url == local_url:
            return

        media_row.local_url = local_url
        await media_row.save()
