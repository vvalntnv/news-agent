import pytest
from database.manager import init_db

pytestmark = pytest.mark.anyio


async def test_database_conn():
    await init_db()
    print("The database connected successfully")
