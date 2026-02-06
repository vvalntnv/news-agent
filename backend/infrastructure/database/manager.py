from tortoise import Tortoise, run_async
from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI

from core.config import config


# TODO: Create a comperhansive DatabaseManager class
async def init_db():
    await Tortoise.init(config=config.tortoise_orm)
    # Generate schemas for safe startup in development
    await Tortoise.generate_schemas()


def init_app_db(app: FastAPI):
    register_tortoise(
        app,
        config=config.tortoise_orm,
        generate_schemas=True,
        add_exception_handlers=True,
    )
