from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "media" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255),
    "site_url" VARCHAR(512) NOT NULL UNIQUE,
    "trustworthiness" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_media_site_ur_1f8d36" ON "media" ("site_url");
COMMENT ON TABLE "media" IS 'Model to store media source information.';
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
CREATE TABLE IF NOT EXISTS "raw_news_data" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "raw_text" TEXT NOT NULL,
    "title" VARCHAR(512) NOT NULL,
    "videos" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "raw_news_data" IS 'Model to store raw news data scraped from websites.';
CREATE TABLE IF NOT EXISTS "article" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "article_url" VARCHAR(1024) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "media_id" INT NOT NULL REFERENCES "media" ("id") ON DELETE CASCADE,
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
    "eJztmv1v2jgYx/8Vi582aVdRrt2m6XQSbemNWwsTZXfTpikyiQNWE5vZTima+r+fbRLy5k"
    "BCgcEuv7Tw+Hkc++O372Pyo+FTB3n8pM0Etj3UeAd+NAj01Yds0SvQgNNpXKAMAo50UAMm"
    "nEZcMGgLaXahx5E0OYjbDE8FpkQ536p4ICjggjIEMHHwA3YC6IGwGg5cRn3gYNdFDBEBfO"
    "RgCDgNmI34iXqKQ235GEzG26owIPh7gCxBx0hMEJPVfv0mzbIu9Ih49HV6b7kYeU4KFHZU"
    "BdpuiflU27pEXGtH1daRZVMv8EnsPJ2LCSVLb0yEso4RQQwKpKoXLFDoSOB5IeSI5qKlsc"
    "uiiYkYB7kw8NQAqOgc/8iYIBiabErU2MnWcN3BsXrKb63Tszdnb39/ffZWuuiWLC1vnhbd"
    "i/u+CNQEesPGky6HAi48NMaYWzg4VsC8PMDLCWRmgpmwDErZgSzKCNwqlpEhhhlP3i3R9O"
    "Gj5SEyFhP59bTZOlsB75/24PJ9e/BCub1U/aFySS2WWi8sa4WFinHM1GZI9dqCIo/0SpYI"
    "7CMz1nRkhqoThp5EHw6UseyD0yfePFwMKwgPu7edu2H79qPqic/5d08jag87qqSlrfOM9c"
    "XrzFgsKwH/dofvgfoKvvR7HU2QcjFm+omx3/BLQ7UJBoJahM4s6CTWbWSNwKQGVu9YVqWt"
    "JhmyfsM5kBHcyp4TYyNoxi29A1VClw3bCF84rEdMj8HZBvAyUVthdwxnnRII7r3xqNNLMY"
    "/wWsoVPCYf0FyT7MomQWIjA7VQjN1G9Rzeyn2KpkFkjQdJTYhINqV2JdlB2S0kFid+++6y"
    "fdVpmNfvFuD1ZF1XYVUHt3TL4svuTGaEaiqOoH0/g8yxUnNSldAWNc7SaOHmWfcJGlL5py"
    "TpAZw9A/au13pZ1Jl9rATpNFhV5Lf8rAUSONbdUq1TbUmtbUMGtlz0xfnXcn+pnH0lMyGZ"
    "ObmU+VC5rs2yVgbW2dTesyn9P0euOI2K/DfKn36CtEmlT63z8xLZk/QqTJ50WVrtcCwqJ6"
    "PJmO1kojufhymQ56etEiClVyFIXZYGKVvMxYwyMcEEcW44uj0KC1a0ITbD1VXBu9JAzZPm"
    "sw8WE8mr/qeLmw74OOhcdu+6/V46v9SFyiQNeHHADDrtmzq3/3Vz+1yyUCzZcjdmhhV1EU"
    "ZefxggT5/DxeoscaN7eMNcJM6e8sJ1e9JrKVYN6ispZIsFWCpPqSzCpozacrNDDlD1AFUP"
    "GM2BlE5ANliSWavGytVQy7K9yzIe+D5k8zy8IXosoJcIOZbL7VWbcefzMLUPR9LhxW3788"
    "vUXnzT7/0VuSekxuVN/yJzFLpydVn2BNn31gaAzdE167WspdA1nD1/3/V7a0FHoRnKn4js"
    "/VcH2+IV8DAX33bFvPGHGxBbsQajAHsCE36iHvhnYycjoZisHoks9IysUBVkR0KWY4EfkE"
    "WnmIRHfNk5b4qtZ7x5xhM0hptyNsXWnM2c64SmTmj2m9Aczr3+TvOZ5P27IaXJXM8XZzXq"
    "Bvx5mY2sIZGRSE84lTmKfhtnhkbq9mx9blO2jjq72Xt2oyaIkGdhlRMyGVOfjOaTUWDhVb"
    "rNXwYcC9E9XEM/YAfRSvlKHFGnKZunKbWs+3/KukqKJqcBiyVg9PLBLywEK2i7NmLYnphk"
    "XViyUtHB2GedlCvuWS209i60HhDjxpuIYkmQCDlOUbCTH/nV0qgAMXQ/ToCnzWapd8ybK1"
    "4xb+beMKdEIGI42otlVSLkZ+mqncn/rSmoXR20pY6Xp/8A3kLK4Q=="
)
