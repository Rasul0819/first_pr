import pytest_asyncio

from database import Database


@pytest_asyncio.fixture
async def db():
    d = Database(":memory:")
    await d.connect()
    yield d
    await d.close()
