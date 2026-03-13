from domain.news.entities import Article
from domain.news.value_objects import ArticleContent
from infrastructure.database.models.article.model import Article as ArticleEntry
from infrastructure.database.models.article.mappers.media_mapper import map_media_rows


def map_article_entry_to_domain(article_entry: ArticleEntry) -> Article | None:
    """Map an article ORM entry to the domain Article model."""

    raw_data = article_entry.raw_data
    if raw_data is None:
        return None

    media_rows = getattr(article_entry, "media_items", [])
    media_items = map_media_rows(list(media_rows))

    return Article(
        article_id=article_entry.id,
        title=raw_data.title,
        content=ArticleContent(
            raw_content=raw_data.raw_text,
            quotes=raw_data.quotes,
        ),
        media=media_items,
        timestamp=raw_data.timestamp,
        author=raw_data.author,
        article_url=article_entry.article_url,
    )
