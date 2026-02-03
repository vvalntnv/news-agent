import asyncio
from tortoise import Tortoise
from backend.database.models import Media, Article, NewsData, RawNewsData


async def init():
    # In-memory SQLite for testing
    await Tortoise.init(
        db_url="sqlite://:memory:", modules={"models": ["backend.database.models"]}
    )
    await Tortoise.generate_schemas()


async def verify():
    await init()

    print("Registered apps:", Tortoise.apps)
    print("Registered models in 'models' app:", Tortoise.apps.get("models", {}).keys())

    # Print schema just in case (for SQLite)
    conn = Tortoise.get_connection("default")
    res = await conn.execute_query("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables in DB:", res)

    schema_res = await conn.execute_query(
        "SELECT sql FROM sqlite_master WHERE type='table';"
    )
    for row in schema_res[1]:
        print(f"Schema: {row[0]}")

    print("Creating Media...")
    media = await Media.create(name="Test Media", site_url="http://test.com")

    print("Creating RawNewsData...")
    raw = await RawNewsData.create(raw_text="Some raw text", title="Test Title")

    print("Creating NewsData...")
    news = await NewsData.create(
        summary="Summary",
        fact_check_summary="Fact check",
        positive_opinion="Positive",
        negative_opinion="Negative",
    )

    print(f"Media ID: {media.id}")
    print(f"RawNewsData ID: {raw.id}")
    print(f"NewsData ID: {news.id}")

    import logging

    logging.basicConfig(level=logging.DEBUG)

    print("Creating Article with only Media...")
    try:
        article_partial = await Article.create(
            media_id=media.id, article_url="http://test.com/article_partial"
        )
        print("Success: Article with only Media created.")
    except Exception as e:
        print(f"Failure: Article with only Media failed: {e}")

    print("Creating Article with Media and NewsData...")
    try:
        article_partial_2 = await Article.create(
            media_id=media.id,
            article_url="http://test.com/article_partial_2",
            news_data_id=news.id,
        )
        print("Success: Article with Media and NewsData created.")
    except Exception as e:
        print(f"Failure: Article with Media and NewsData failed: {e}")

    print("Creating full Article...")
    article = await Article.create(
        media_id=media.id,
        article_url="http://test.com/article",
        news_data_id=news.id,
        raw_data_id=raw.id,
    )

    print("Verifying relationships...")
    # Fetch article with relations
    fetched_article = (
        await Article.filter(id=article.id)
        .prefetch_related("media", "news_data", "raw_data")
        .first()
    )

    assert fetched_article.media.name == "Test Media"
    assert fetched_article.news_data.summary == "Summary"
    assert fetched_article.raw_data.title == "Test Title"

    # Check reverse relations
    fetched_news = (
        await NewsData.filter(id=news.id).prefetch_related("articles").first()
    )
    assert len(fetched_news.articles) == 1
    assert fetched_news.articles[0].article_url == "http://test.com/article"

    print("Verification successful!")


if __name__ == "__main__":
    asyncio.run(verify())
