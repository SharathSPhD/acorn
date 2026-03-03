__pattern__ = "Repository"

from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
from enum import Enum


class ProblemStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    FAILED = "failed"


class TaskType(str, Enum):
    INGEST = "ingest"
    ANALYSE = "analyse"
    MODEL = "model"
    SYNTHESISE = "synthesise"
    VALIDATE = "validate"


class ProblemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    idempotency_key: Optional[str] = None


class ProblemResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: ProblemStatus
    solution_url: Optional[str]
    created_at: datetime


class TaskCreate(BaseModel):
    problem_id: UUID
    title: str
    description: Optional[str] = None
    task_type: TaskType
    blocked_by: list[UUID] = Field(default_factory=list)


class TaskResponse(BaseModel):
    id: UUID
    problem_id: UUID
    title: str
    task_type: TaskType
    status: str
    assigned_to: Optional[str]
    created_at: datetime


class AgentEvent(BaseModel):
    event_type: str
    agent_id: str
    problem_uuid: str
    timestamp_utc: float
    schema_version: str = "1.0"
    payload: dict = Field(default_factory=dict)
