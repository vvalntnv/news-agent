from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "media" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "media_type" VARCHAR(64) NOT NULL,
            "article_url" VARCHAR(2048) NOT NULL,
            "local_url" VARCHAR(2048),
            "article_id" INT NOT NULL REFERENCES "article" ("id") ON DELETE CASCADE,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_media_article_id" ON "media" ("article_id");
        CREATE INDEX IF NOT EXISTS "idx_media_article_url" ON "media" ("article_url");
        ALTER TABLE "article"
        ALTER COLUMN "media_id" DROP NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "media";
        ALTER TABLE "article"
        ALTER COLUMN "media_id" SET NOT NULL;
    """
