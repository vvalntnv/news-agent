from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "raw_news_data"
        ADD COLUMN IF NOT EXISTS "author" VARCHAR(256) NOT NULL DEFAULT '';
        ALTER TABLE "raw_news_data"
        ADD COLUMN IF NOT EXISTS "timestamp" VARCHAR(128) NOT NULL DEFAULT '';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "raw_news_data"
        DROP COLUMN IF EXISTS "author";
        ALTER TABLE "raw_news_data"
        DROP COLUMN IF EXISTS "timestamp";
    """
