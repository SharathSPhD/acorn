__pattern__ = "Repository"

from uuid import UUID

from memory.interfaces import SkillRepository, Skill, PromotionThresholdNotMet
from api.config import settings


class FilesystemSkillRepository(SkillRepository):
    """Production: reads SKILL.md files from probationary/ and permanent/ directories."""

    def __init__(self, permanent_path: str, probationary_path: str, db_url: str):
        self._permanent = permanent_path
        self._probationary = probationary_path
        self._db_url = db_url

    async def find_by_keywords(self, query: str, category: str | None = None, top_k: int = 5) -> list[Skill]:
        # TODO Phase 3: use pgvector similarity search
        raise NotImplementedError("Phase 3")

    async def promote(self, skill_id: UUID) -> None:
        # TODO Phase 3: check use_count >= threshold, move file, UPDATE skills table
        raise NotImplementedError("Phase 3")

    async def deprecate(self, skill_id: UUID, reason: str) -> None:
        raise NotImplementedError("Phase 3")
