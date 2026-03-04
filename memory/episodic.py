__pattern__ = "Repository"

from uuid import UUID

from memory.interfaces import Episode, EpisodicMemoryRepository


class PostgresEpisodicMemoryRepository(EpisodicMemoryRepository):
    """Production: stores episodes in PostgreSQL with pgvector embeddings."""

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url

    async def store(self, episode: Episode) -> UUID:
        # TODO Phase 3: INSERT into episodes with embedding
        raise NotImplementedError("Phase 3")

    async def retrieve_similar(self, query_embedding: list[float], top_k: int = 5) -> list[Episode]:
        # TODO Phase 3: SELECT ... ORDER BY embedding <=> $1 LIMIT top_k
        raise NotImplementedError("Phase 3")

    async def mark_retrieved(self, episode_id: UUID) -> None:
        # TODO Phase 3: UPDATE episodes SET retrieved_count = retrieved_count + 1
        raise NotImplementedError("Phase 3")
