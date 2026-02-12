from domain.news.entities import Article
from domain.news.protocols import ArticleRepository
from domain.news.value_objects import ArticleContent
from infrastructure.database.models.raw_news_data import RawNewsData


class TortoiseArticleRepository(ArticleRepository):
    """
    Tortoise ORM implementation of the ArticleRepository.
    """

    async def save(self, article: Article) -> Article:
        # Convert Domain Article to DB Model
        # We try to find existing one by URL if possible, or just create new.
        # If ID exists, we update. But Article entity doesn't have ID yet.
        # Assuming we treat URL as unique identifier.

        raw_news_data = None
        if article.source_url:
            raw_news_data = await RawNewsData.filter(url=article.source_url).first()

        if raw_news_data:
            raw_news_data.title = article.title
            raw_news_data.raw_text = article.content.raw_content
            raw_news_data.quotes = article.content.quotes
            raw_news_data.videos = article.videos
            await raw_news_data.save()
        else:
            raw_news_data = await RawNewsData.create(
                title=article.title,
                raw_text=article.content.raw_content,
                quotes=article.content.quotes,
                videos=article.videos,
                url=article.source_url,
            )

        return article  # In a real app we might return updated entity with ID

    async def get_by_url(self, url: str) -> Article | None:
        raw_news_data = await RawNewsData.filter(url=url).first()
        if raw_news_data:
            loaded_videos = self._as_string_list(raw_news_data.videos)
            loaded_quotes = self._as_string_list(raw_news_data.quotes)
            return Article(
                title=raw_news_data.title,
                content=ArticleContent(
                    raw_content=raw_news_data.raw_text,
                    quotes=loaded_quotes,
                ),
                videos=loaded_videos,
                timestamp="",
                author="",
                source_url=raw_news_data.url,
            )
        return None

    def _as_string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []

        return [item for item in value if isinstance(item, str)]
