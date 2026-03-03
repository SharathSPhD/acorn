__pattern__ = "Factory"

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from api.dependencies import get_settings
from api.config import OAKSettings

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/spawn")
async def spawn_agent(
    role: str,
    problem_uuid: UUID,
    settings: OAKSettings = Depends(get_settings),
):
    """Spawn an agent for a problem via AgentFactory. Returns container ID."""
    raise HTTPException(status_code=501, detail="Phase 1: not yet implemented")
