"""Tests for FilesystemKernelRepository (memory/kernels.py)."""
import pytest
from uuid import uuid4

from memory.kernels import FilesystemKernelRepository


def test_fs_kernel_repo__init__stores_paths():
    repo = FilesystemKernelRepository("/perm", "/prob", "postgresql://x")
    assert repo._permanent == "/perm"
    assert repo._probationary == "/prob"
    assert repo._db_url == "postgresql://x"


@pytest.mark.asyncio
async def test_fs_kernel_repo__find_by_keywords__raises_not_implemented():
    repo = FilesystemKernelRepository("/p", "/q", "pg://x")
    with pytest.raises(NotImplementedError, match="Phase 3"):
        await repo.find_by_keywords("test")


@pytest.mark.asyncio
async def test_fs_kernel_repo__promote__raises_not_implemented():
    repo = FilesystemKernelRepository("/p", "/q", "pg://x")
    with pytest.raises(NotImplementedError, match="Phase 3"):
        await repo.promote(uuid4())


@pytest.mark.asyncio
async def test_fs_kernel_repo__deprecate__raises_not_implemented():
    repo = FilesystemKernelRepository("/p", "/q", "pg://x")
    with pytest.raises(NotImplementedError, match="Phase 3"):
        await repo.deprecate(uuid4(), "stale")
