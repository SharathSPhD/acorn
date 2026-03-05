__pattern__ = "Repository"

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from api.services.reward_service import RewardService

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("/events")
async def list_reward_events(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    svc = RewardService()
    return await svc.get_recent_events(limit=limit)


@router.get("/role-scores")
async def get_role_scores() -> list[dict[str, Any]]:
    svc = RewardService()
    return await svc.get_all_role_scores()


@router.get("/role-context/{role}")
async def get_role_context(role: str) -> dict[str, Any]:
    svc = RewardService()
    return await svc.get_role_context(role)


@router.post("/record", status_code=201)
async def record_reward(request: Request) -> dict[str, Any]:
    body = await request.json()
    signal = body.get("signal")
    if not signal:
        raise HTTPException(status_code=400, detail="signal is required")
    agent_id = body.get("agent_id", "unknown")
    role = body.get("role", "unknown")

    svc = RewardService()
    result = await svc.record_reward(
        signal=signal,
        agent_id=agent_id,
        role=role,
        problem_id=body.get("problem_id"),
        task_id=body.get("task_id"),
        points=body.get("points"),
        rationale=body.get("rationale"),
    )
    return result
