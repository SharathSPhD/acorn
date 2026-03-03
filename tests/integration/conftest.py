"""Integration test fixtures — require real database containers."""
import pytest_asyncio
from api.db.connection import AsyncSessionLocal


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
