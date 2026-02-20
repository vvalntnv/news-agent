from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "raw_news_data"
        ADD COLUMN IF NOT EXISTS "quotes" JSONB NOT NULL DEFAULT '[]';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "raw_news_data"
        DROP COLUMN IF EXISTS "quotes";
    """
