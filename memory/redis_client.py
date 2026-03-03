__pattern__ = "Repository"

import json

import redis.asyncio as redis

from memory.interfaces import WorkingMemoryRepository, SessionState
from api.config import settings


class RedisWorkingMemoryRepository(WorkingMemoryRepository):
    """Production: per-agent key-value store with TTL."""

    def __init__(self, redis_url: str, ttl_hours: int):
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_hours * 3600

    def _key(self, agent_id: str, key: str) -> str:
        return f"oak:session:{agent_id}:{key}"

    async def set(self, agent_id: str, key: str, value: str) -> None:
        await self._client.setex(self._key(agent_id, key), self._ttl, value)

    async def get(self, agent_id: str, key: str) -> str | None:
        return await self._client.get(self._key(agent_id, key))

    async def restore_session(self, agent_id: str) -> SessionState:
        # TODO Phase 1: restore all session keys from Redis
        raise NotImplementedError("Phase 1")
