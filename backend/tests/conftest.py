from __future__ import annotations

import re
from collections.abc import AsyncIterator
from urllib.parse import quote

import asyncpg
import pytest
from faker import Faker
from tortoise import Tortoise

from core.config import config
from infrastructure.database.repositories import TortoiseArticleRepository
from tests.utils.factories import ArticleFactory

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


def _build_test_db_name() -> str:
    return f"{config.db_name}_test"


def _build_test_db_user() -> str:
    return config.db_user


def _validate_identifier(identifier: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier}")
    return identifier


def _build_database_dsn() -> str:
    return (
        f"postgres://{quote(config.db_user)}:{quote(config.db_pass)}"
        f"@{config.db_host}:{config.db_port}/{config.db_name}"
    )


def _build_test_dsn(test_db_user: str, test_db_name: str) -> str:
    return (
        f"postgres://{quote(test_db_user)}:{quote(config.db_pass)}"
        f"@{config.db_host}:{config.db_port}/{test_db_name}"
    )


async def _ensure_test_database_exists(
    connection: asyncpg.Connection,
    database_name: str,
    owner_role_name: str,
) -> None:
    safe_database_name = _validate_identifier(database_name)
    safe_owner_role_name = _validate_identifier(owner_role_name)

    database_exists = await connection.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1",
        database_name,
    )
    if database_exists:
        await connection.execute(f"DROP DATABASE {safe_database_name} WITH (FORCE)")

    await connection.execute(
        f"CREATE DATABASE {safe_database_name} OWNER {safe_owner_role_name}"
    )


def _build_tortoise_test_config(test_dsn: str) -> dict[str, dict[str, object]]:
    return {
        "connections": {"default": test_dsn},
        "apps": {
            "models": {
                "models": ["infrastructure.database.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }


async def _truncate_test_tables() -> None:
    connection = Tortoise.get_connection("default")
    await connection.execute_script(
        "TRUNCATE TABLE media, article, raw_news_data, news_data, news_media "
        "RESTART IDENTITY CASCADE;"
    )


@pytest.fixture(autouse=True, scope="session")
async def initialized_test_database(anyio_backend) -> AsyncIterator[str]:
    del anyio_backend
    test_db_name = _build_test_db_name()
    test_db_user = _build_test_db_user()

    admin_connection = await asyncpg.connect(_build_database_dsn())
    try:
        try:
            await _ensure_test_database_exists(
                admin_connection,
                test_db_name,
                test_db_user,
            )
        except asyncpg.exceptions.InsufficientPrivilegeError as error:
            pytest.skip(
                f"Postgres user lacks permissions to create test role/database: {error}"
            )
    finally:
        await admin_connection.close()

    test_dsn = _build_test_dsn(test_db_user, test_db_name)
    await Tortoise.init(config=_build_tortoise_test_config(test_dsn))
    await Tortoise.generate_schemas(safe=True)
    await _truncate_test_tables()

    yield test_dsn

    await Tortoise.close_connections()


@pytest.fixture()
async def clean_database_tables() -> None:
    # Cleanup
    await _truncate_test_tables()


@pytest.fixture()
def article_repository() -> TortoiseArticleRepository:
    return TortoiseArticleRepository()


@pytest.fixture()
def faker_instance() -> Faker:
    faker = Faker(locale=["en_US", "bg_BG", "de_DE"])
    return faker


@pytest.fixture()
def article_factory(faker_instance: Faker) -> ArticleFactory:
    return ArticleFactory(faker=faker_instance)
