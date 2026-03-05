"""Judge verdict router — Phase 2 gate."""
__pattern__ = "Observer"

import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.connection import get_db
from api.dependencies import get_event_bus
from api.events.bus import AgentEvent, EventBus
from api.models import JudgeVerdictCreate, JudgeVerdictResponse

router = APIRouter(prefix="/api/judge_verdicts", tags=["judge"])


@router.post("", response_model=JudgeVerdictResponse, status_code=status.HTTP_201_CREATED)
async def submit_verdict(
    body: JudgeVerdictCreate,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> JudgeVerdictResponse:
    """Submit a judge verdict for a task. Publishes judge_verdict event."""
    verdict_id = uuid4()
    result = await db.execute(
        text("""
            INSERT INTO judge_verdicts (id, task_id, verdict, checks, notes)
            VALUES (:id, :task_id, :verdict, CAST(:checks AS jsonb), :notes)
            RETURNING id, task_id, verdict, checks, notes, created_at
        """),
        {
            "id": str(verdict_id),
            "task_id": str(body.task_id),
            "verdict": body.verdict,
            "checks": __import__("json").dumps(body.checks),
            "notes": body.notes,
        },
    )
    await db.commit()
    row = result.mappings().one()
    await bus.publish(AgentEvent(
        event_type="judge_verdict",
        agent_id="judge",
        problem_uuid="",
        payload={"task_id": str(body.task_id), "verdict": body.verdict},
        timestamp_utc=time.time(),
    ))

    # C3C: On FAIL verdict, check if any role's rolling_30d score is below threshold.
    # If so, publish calibration_needed event for the Meta-Agent to act on.
    if body.verdict == "fail":
        try:
            import asyncpg  # noqa: I001
            from api.config import settings as _cfg  # noqa: I001
            _conn = await asyncpg.connect(_cfg.database_url)
            try:
                low_roles = await _conn.fetch(
                    """SELECT role, rolling_30d_points FROM role_scores
                       WHERE rolling_30d_points < 0
                       ORDER BY rolling_30d_points ASC LIMIT 5""",
                )
                if low_roles:
                    await bus.publish(AgentEvent(
                        event_type="calibration_needed",
                        agent_id="judge",
                        problem_uuid="",
                        payload={
                            "trigger": "judge_fail",
                            "task_id": str(body.task_id),
                            "low_roles": [
                                {"role": r["role"], "score": r["rolling_30d_points"]}
                                for r in low_roles
                            ],
                        },
                        timestamp_utc=time.time(),
                    ))
            finally:
                await _conn.close()
        except Exception:
            pass  # Non-blocking; calibration trigger best-effort

    return JudgeVerdictResponse(**dict(row))


@router.get("/check/{task_id}")
async def check_verdict(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Check if a task has a passing judge verdict. Used by thin hooks."""
    result = await db.execute(
        text(
            "SELECT COUNT(*) AS cnt FROM judge_verdicts"
            " WHERE task_id = :task_id AND verdict = 'pass'"
        ),
        {"task_id": str(task_id)},
    )
    row = result.mappings().one()
    return {"has_pass": int(row["cnt"]) > 0}


@router.get("/{problem_uuid}", response_model=list[JudgeVerdictResponse])
async def get_verdicts(
    problem_uuid: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[JudgeVerdictResponse]:
    """Return all judge verdicts for tasks belonging to a problem."""
    result = await db.execute(
        text("""
            SELECT jv.id, jv.task_id, jv.verdict, jv.checks, jv.notes, jv.created_at
            FROM judge_verdicts jv
            JOIN tasks t ON t.id = jv.task_id
            WHERE t.problem_id = :problem_uuid
            ORDER BY jv.created_at DESC
        """),
        {"problem_uuid": str(problem_uuid)},
    )
    return [JudgeVerdictResponse(**dict(row)) for row in result.mappings()]
