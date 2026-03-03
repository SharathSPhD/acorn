"""Integration tests for database connectivity (requires real PG)."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_db_connection__get_db__yields_session(db_session: AsyncSession):
    """Smoke: get_db yields a live AsyncSession against a real PG container."""
    assert isinstance(db_session, AsyncSession)
