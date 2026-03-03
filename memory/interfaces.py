__pattern__ = "Repository"

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Episode:
    id: UUID
    problem_id: Optional[UUID]
    agent_id: str
    event_type: str
    content: str
    embedding: Optional[list[float]] = None
    retrieved_count: int = 0
    last_retrieved_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class Skill:
    id: UUID
    name: str
    category: str
    description: str
    trigger_keywords: list[str] = field(default_factory=list)
    embedding: Optional[list[float]] = None
    status: str = "probationary"
    use_count: int = 0
    verified_on_problems: list[UUID] = field(default_factory=list)
    filesystem_path: Optional[str] = None
    deprecated_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SessionState:
    agent_id: str
    keys: dict[str, str] = field(default_factory=dict)


class PromotionThresholdNotMet(Exception):
    pass


class EpisodicMemoryRepository(ABC):
    @abstractmethod
    async def store(self, episode: Episode) -> UUID: ...

    @abstractmethod
    async def retrieve_similar(self, query_embedding: list[float],
                               top_k: int = 5) -> list[Episode]: ...

    @abstractmethod
    async def mark_retrieved(self, episode_id: UUID) -> None: ...


class SkillRepository(ABC):
    @abstractmethod
    async def find_by_keywords(self, query: str, category: str | None = None,
                               top_k: int = 5) -> list[Skill]: ...

    @abstractmethod
    async def promote(self, skill_id: UUID) -> None: ...

    @abstractmethod
    async def deprecate(self, skill_id: UUID, reason: str) -> None: ...


class WorkingMemoryRepository(ABC):
    """Redis-backed; all keys are TTL-scoped to OAK_SESSION_TTL_HOURS."""
    @abstractmethod
    async def set(self, agent_id: str, key: str, value: str) -> None: ...

    @abstractmethod
    async def get(self, agent_id: str, key: str) -> str | None: ...

    @abstractmethod
    async def restore_session(self, agent_id: str) -> SessionState: ...
