__pattern__ = "Repository"

from uuid import UUID

from memory.interfaces import Kernel, KernelRepository


class FilesystemKernelRepository(KernelRepository):
    """Production: reads KERNEL.md files from probationary/ and permanent/ directories."""

    def __init__(
        self, permanent_path: str, probationary_path: str, db_url: str
    ) -> None:
        self._permanent = permanent_path
        self._probationary = probationary_path
        self._db_url = db_url

    async def find_by_keywords(
        self, query: str, category: str | None = None, top_k: int = 5
    ) -> list[Kernel]:
        # TODO Phase 3: use pgvector similarity search
        raise NotImplementedError("Phase 3")

    async def promote(self, kernel_id: UUID) -> None:
        # TODO Phase 3: check use_count >= threshold, move file, UPDATE kernels table
        raise NotImplementedError("Phase 3")

    async def deprecate(self, kernel_id: UUID, reason: str) -> None:
        raise NotImplementedError("Phase 3")
