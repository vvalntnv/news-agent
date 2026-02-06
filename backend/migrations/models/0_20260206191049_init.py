from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "news_data" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "summary" TEXT NOT NULL,
    "fact_check_summary" TEXT NOT NULL,
    "fact_check_urls" JSONB NOT NULL,
    "positive_opinion" TEXT NOT NULL,
    "negative_opinion" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "news_data" IS 'Model to store processed news data by the agents.';
CREATE TABLE IF NOT EXISTS "news_media" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255),
    "site_url" VARCHAR(512) NOT NULL UNIQUE,
    "trustworthiness" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_news_media_site_ur_410828" ON "news_media" ("site_url");
COMMENT ON TABLE "news_media" IS 'Model to store media source information.';
CREATE TABLE IF NOT EXISTS "raw_news_data" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "raw_text" TEXT NOT NULL,
    "title" VARCHAR(512) NOT NULL,
    "url" VARCHAR(2048) UNIQUE,
    "videos" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "raw_news_data" IS 'Model to store raw news data scraped from websites.';
CREATE TABLE IF NOT EXISTS "article" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "article_url" VARCHAR(1024) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "media_id" INT NOT NULL REFERENCES "news_media" ("id") ON DELETE CASCADE,
    "news_data_id" INT REFERENCES "news_data" ("id") ON DELETE CASCADE,
    "raw_data_id" INT UNIQUE REFERENCES "raw_news_data" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "article" IS 'Model to store individual articles from different media sources.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmv1v2jgYx/8VKz910q6iXLtV03QSbemNWwsTZXfTTqfIJAasJjaznVK06/9+tknImw"
    "MJBVZ2+WUrj/049sdv3+dJvls+dZHHj1tMYMdD1jvw3SLQV39ki14DC06ncYEyCDjUThZM"
    "VBpywaAjpHkEPY6kyUXcYXgqMCWq8q3yB4ICLihDABMXP2A3gB4Im+FgxKgPXDwaIYaIAD"
    "5yMQScBsxB/Fg9xaWOfAwm4201GBD8LUC2oGMkJojJZv/+R5plW+gR8ejn9N4eYeS5KVDY"
    "VQ1ouy3mU23rEHGtK6q+Dm2HeoFP4srTuZhQsqyNiVDWMSKIQYFU84IFCh0JPC+EHNFc9D"
    "SusuhiwsdFIxh4agKUd45/ZEwQDE0OJWruZG+4HuBYPeWX5snp29PzX9+cnssquidLy9un"
    "xfDisS8cNYHuwHrS5VDARQ2NMeYWTo4dMC8P8HICmZlgxi2DUg4gizICt4plZIhhxot3Sz"
    "R9+Gh7iIzFRP48aTRPV8D7s9W//NDqH6lqr9R4qNxSi63WDcuaYaFiHDN1GFKjtqHII72S"
    "JQL7yIw17Zmh6oaux9EfL5SxHIPbI9483AwrCA86t+27Qev2kxqJz/k3TyNqDdqqpKmt84"
    "z16E1mLpaNgL86gw9A/QRfe922Jki5GDP9xLje4Kul+gQDQW1CZzZ0E/s2skZgUhOrTyy7"
    "0lGTdFl/4LyQGdzKmRNjI2jGbX0CVUKXddsIXzitB0yPwdkG8DJeW2F3CHedEgije+NVp7"
    "diHuG1lCt4TD6iuSbZkV2CxEEGaqEY68p1eRu19fJ271O0FCJrPFFqUUTSKXUyyUHKoSGx"
    "uPVbd5etq7Zl3sNbAngVNvXitm9ZfNnTyYxQLcchdO5nkLl2al2qEtqkxpUabd486x5BAy"
    "r/KUm6D2fPgL3r/V4WdeYsK0E6DVYV+U0/a4EEjvWwVO9UX7LL0xCIJWkWR2KpzVI5Fpsy"
    "KgMijlyg2gGqHTCcAxkRAdlhyW5t8FWuhTra2nu0xQPfh2yehzdAjwX0Ei6HEmWtUvztL4"
    "OU2I8iqaPb1pdXKcF/0+v+HlVPRF6XN72LjEIayd1lOxPk3NsbADZ716zXspaxP8+D/uOu"
    "110LOnLNRrjYEeBf4GG+s8jIej8KiKMog2GAPYEJP1bP+83ayRwoGqvnIIv7dTpqVQ1k50"
    "CWY4EfkE2nmKi+VljtJt96rZvXOkFjuClnk2/N2cy5zpf9RPmyXABeHALlstCG6+Qi9Lz+"
    "2EceFOadlH9LcjBh5VM+DtxuJLPIVBSEMss0xppYZpk6qRzMJF/yAExGlPl6FtfGMCsd69"
    "Bl76GL/j9HrvgNUVR/o0vvB2RtU2+GmmdnJV4MyVqF74V0Wfqak8Kr8nu2pM925MPO12EK"
    "5NlJswRIWasQpC5Lg5Q95mJGmZhggrjh0rj2KCzY0QbfDNeRct6VVGgcN3aiy656ny9u2u"
    "BTv33ZueuEMcdSCuhCZZIGvMib9dutm1qG1TLsh8qwF/R2ZKc6LJmGNyixTJa+WIupRPjz"
    "csuyhUROWNaEU+QuPsyZoaG6bdZnl8u2UYu0vYs0tUAEejQc4MWZiqRPnaEwZygEFl4l9b"
    "t0OBSie5BtFaXvc1Tv3r9cSEcPjdPzMuGDrFYcP+jCNMAH7CJaKeUee9SZ9k0y7bUk/n9K"
    "4kpiMKefi+Vz9PnGT5zLrCCLW4hhZ2IZFHFYslIMw7jOOhVcPLJao+5doz4gxo0v04qlQM"
    "LlMPXUTvKJamtUgBhWP0yAJ41GqS/1Gys+1G/kvtOnRCBiuNqLBVXCZf+Kamcx09a0066u"
    "2FIXy9N/wGwwCQ=="
)
