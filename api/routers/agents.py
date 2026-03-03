__pattern__ = "Factory"

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from api.dependencies import get_settings
from api.config import OAKSettings
from api.models import AgentStatusResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/spawn")
async def spawn_agent(
    role: str,
    problem_uuid: UUID,
    settings: OAKSettings = Depends(get_settings),
):
    """Spawn an agent for a problem via DGXAgentFactory. Returns container ID."""
    from api.factories.agent_factory import DGXAgentFactory, ResourceCapExceeded
    from api.services.agent_registry import AgentRegistry
    try:
        factory = DGXAgentFactory()
        spec = factory.create(role, str(problem_uuid))
        container_id = factory.launch(spec)
        registry = AgentRegistry(str(settings.redis_url))
        await registry.register(spec.agent_id, role, str(problem_uuid), container_id)
        return {"agent_id": spec.agent_id, "container_id": container_id, "role": role}
    except ResourceCapExceeded as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/status", response_model=list[AgentStatusResponse])
async def get_agents_status(
    settings: OAKSettings = Depends(get_settings),
) -> list[AgentStatusResponse]:
    """Returns status of all active agent sessions from Redis."""
    from api.services.agent_registry import AgentRegistry
    registry = AgentRegistry(str(settings.redis_url))
    return await registry.get_all()
