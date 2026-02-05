import os
from tortoise import Tortoise, run_async
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

# Database URL - using env var or default to local postgres

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "news_agent")

DB_URL = f"postgres://{quote(DB_USER)}:{quote(DB_PASS)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": ["infrastructure.database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}


# TODO: Create a comperhansive DatabaseManager class
async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    # Generate schemas for safe startup in development
    await Tortoise.generate_schemas()


def init_app_db(app: FastAPI):
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        generate_schemas=True,
        add_exception_handlers=True,
    )
