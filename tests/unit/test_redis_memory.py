"""Unit tests for RedisWorkingMemoryRepository."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

redis = pytest.importorskip("redis", reason="redis not installed")
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_redis_working_memory__set__calls_setex():
    """set stores value with correct TTL."""
    mock_client = MagicMock()
    mock_client.setex = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_client):
        from memory.redis_client import RedisWorkingMemoryRepository
        repo = RedisWorkingMemoryRepository(redis_url="redis://test", ttl_hours=2)

    await repo.set("agent-1", "task", "do-thing")
    mock_client.setex.assert_called_once_with(
        "acorn:session:agent-1:task", 7200, "do-thing"
    )


@pytest.mark.asyncio
async def test_redis_working_memory__get__returns_value():
    """get returns stored string value."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value="stored-val")

    with patch("redis.asyncio.from_url", return_value=mock_client):
        from memory.redis_client import RedisWorkingMemoryRepository
        repo = RedisWorkingMemoryRepository(redis_url="redis://test", ttl_hours=1)

    result = await repo.get("agent-1", "task")
    assert result == "stored-val"


@pytest.mark.asyncio
async def test_redis_working_memory__restore_session__builds_state():
    """restore_session rebuilds SessionState from all agent keys."""
    mock_client = MagicMock()
    mock_client.keys = AsyncMock(return_value=[
        "acorn:session:agent-1:step", "acorn:session:agent-1:model",
    ])
    mock_client.get = AsyncMock(side_effect=["execute", "qwen3-coder"])

    with patch("redis.asyncio.from_url", return_value=mock_client):
        from memory.redis_client import RedisWorkingMemoryRepository
        repo = RedisWorkingMemoryRepository(redis_url="redis://test", ttl_hours=1)

    state = await repo.restore_session("agent-1")
    assert state.agent_id == "agent-1"
    assert state.keys == {"step": "execute", "model": "qwen3-coder"}
