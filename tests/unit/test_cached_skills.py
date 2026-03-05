"""Unit tests for CachedKernelRepository Decorator pattern."""
import pytest
import time
from unittest.mock import AsyncMock
from uuid import uuid4
from memory.cached_kernels import CachedKernelRepository
from memory.interfaces import Kernel


def make_kernel(name: str = "test") -> Kernel:
    return Kernel(
        id=uuid4(),
        name=name,
        category="infra",
        description="test skill",
        trigger_keywords=[name],
        status="probationary",
        use_count=0,
    )


@pytest.mark.asyncio
async def test_cached_skills__hit__does_not_call_wrapped():
    wrapped = AsyncMock()
    wrapped.find_by_keywords.return_value = [make_kernel()]
    repo = CachedKernelRepository(wrapped, ttl_seconds=60)

    r1 = await repo.find_by_keywords("etl")
    r2 = await repo.find_by_keywords("etl")

    assert wrapped.find_by_keywords.call_count == 1
    assert r1 == r2


@pytest.mark.asyncio
async def test_cached_skills__miss__different_query():
    wrapped = AsyncMock()
    wrapped.find_by_keywords.return_value = []
    repo = CachedKernelRepository(wrapped)

    await repo.find_by_keywords("etl")
    await repo.find_by_keywords("ml")

    assert wrapped.find_by_keywords.call_count == 2


@pytest.mark.asyncio
async def test_cached_skills__ttl_expired__calls_wrapped_again():
    wrapped = AsyncMock()
    wrapped.find_by_keywords.return_value = []
    repo = CachedKernelRepository(wrapped, ttl_seconds=0.01)

    await repo.find_by_keywords("etl")
    time.sleep(0.02)
    await repo.find_by_keywords("etl")

    assert wrapped.find_by_keywords.call_count == 2


@pytest.mark.asyncio
async def test_cached_skills__promote__delegates_to_wrapped():
    wrapped = AsyncMock()
    repo = CachedKernelRepository(wrapped)
    uid = uuid4()
    await repo.promote(uid)
    wrapped.promote.assert_called_once_with(uid)


@pytest.mark.asyncio
async def test_cached_skills__lru_eviction__removes_oldest():
    wrapped = AsyncMock()
    wrapped.find_by_keywords.return_value = []
    repo = CachedKernelRepository(wrapped, max_size=2)

    await repo.find_by_keywords("a")
    await repo.find_by_keywords("b")
    await repo.find_by_keywords("c")  # evicts "a"

    assert len(repo._cache) == 2
    assert ("a", None, 5) not in repo._cache
