__pattern__ = "Factory"

import time
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, status

from api.config import OAKSettings
from api.dependencies import get_settings, get_event_bus
from api.models import ProblemCreate, ProblemResponse
from api.events.bus import EventBus, AgentEvent

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.post("", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    body: ProblemCreate,
    settings: OAKSettings = Depends(get_settings),
    bus: EventBus = Depends(get_event_bus),
):
    """Create a new problem. Returns 429 if MAX_CONCURRENT_PROBLEMS exceeded."""
    # TODO Phase 2: check concurrent problem cap against DB
    # For Phase 0: just create and return
    problem_id = uuid4()
    await bus.publish(AgentEvent(
        event_type="problem_created",
        agent_id="system",
        problem_uuid=str(problem_id),
        timestamp_utc=time.time(),
        payload={"title": body.title},
    ))
    # TODO: persist to DB
    raise HTTPException(status_code=501, detail="Phase 0: DB persistence not yet wired")


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(problem_id: UUID):
    """Get problem by ID."""
    raise HTTPException(status_code=501, detail="Phase 0: not yet implemented")
