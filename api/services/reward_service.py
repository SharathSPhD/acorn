__pattern__ = "Repository"

import logging
import uuid as uuid_mod
from typing import Any

import asyncpg

from api.config import settings

logger = logging.getLogger(__name__)

REWARD_SIGNALS = {
    "JUDGE_PASS": 10,
    "SOLUTION_COMPLETE": 15,
    "KERNEL_PROMOTED": 25,
    "NOVEL_DOMAIN": 50,
    "REASONING_DEPTH": 3,
    "KERNEL_QUERY_HIT": 4,
    "MAILBOX_COORDINATION": 2,
    "FAST_TASK_CLAIM": 1,
    "CITE_VERIFIED": 3,
    "METRIC_VERIFIED": 8,
}

PENALTY_SIGNALS = {
    "JUDGE_FAIL": -5,
    "MISSING_REASONING_TRAIL": -3,
    "HALLUCINATED_CITATION": -10,
    "SHALLOW_REASONING": -2,
    "EMPTY_RESEARCH": -3,
}


class RewardService:
    """Records reward/penalty signals and maintains per-role scores."""

    async def record_reward(
        self,
        signal: str,
        agent_id: str,
        role: str,
        problem_id: str | None = None,
        task_id: str | None = None,
        points: int | None = None,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        if points is None:
            points = REWARD_SIGNALS.get(signal, PENALTY_SIGNALS.get(signal, 0))

        conn = await asyncpg.connect(settings.database_url)
        try:
            pid = uuid_mod.UUID(problem_id) if problem_id else None
            tid = uuid_mod.UUID(task_id) if task_id else None
            row = await conn.fetchrow(
                """INSERT INTO reward_events
                   (problem_id, task_id, agent_id, role, signal, points, rationale)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING id, created_at""",
                pid, tid, agent_id, role, signal, points, rationale,
            )
            await conn.execute(
                """INSERT INTO role_scores
                   (role, cumulative_points, rolling_30d_points, problems_contributed)
                   VALUES ($1, $2::bigint, $3::integer, 1)
                   ON CONFLICT (role) DO UPDATE SET
                       cumulative_points = role_scores.cumulative_points + $2::bigint,
                       rolling_30d_points = (
                           SELECT COALESCE(SUM(points), 0)
                           FROM reward_events
                           WHERE role = $1 AND created_at > NOW() - INTERVAL '30 days'
                       ),
                       problems_contributed = (
                           SELECT COUNT(DISTINCT problem_id)
                           FROM reward_events
                           WHERE role = $1 AND problem_id IS NOT NULL
                       ),
                       last_updated = NOW()""",
                role, points,
            )
            return {"id": str(row["id"]), "created_at": str(row["created_at"]), "points": points}
        finally:
            await conn.close()

    async def get_role_context(self, role: str) -> dict[str, Any]:
        conn = await asyncpg.connect(settings.database_url)
        try:
            wins = await conn.fetch(
                """SELECT signal, points, rationale, created_at
                   FROM reward_events WHERE role = $1 AND points > 0
                   ORDER BY created_at DESC LIMIT 5""",
                role,
            )
            misses = await conn.fetch(
                """SELECT signal, points, rationale, created_at
                   FROM reward_events WHERE role = $1 AND points < 0
                   ORDER BY created_at DESC LIMIT 5""",
                role,
            )
            score_row = await conn.fetchrow(
                "SELECT * FROM role_scores WHERE role = $1", role,
            )
            return {
                "role": role,
                "recent_wins": [
                    {"signal": r["signal"], "points": r["points"],
                     "rationale": r["rationale"], "at": str(r["created_at"])}
                    for r in wins
                ],
                "recent_misses": [
                    {"signal": r["signal"], "points": r["points"],
                     "rationale": r["rationale"], "at": str(r["created_at"])}
                    for r in misses
                ],
                "score": {
                    "cumulative": score_row["cumulative_points"] if score_row else 0,
                    "rolling_30d": score_row["rolling_30d_points"] if score_row else 0,
                    "problems": score_row["problems_contributed"] if score_row else 0,
                } if score_row else {"cumulative": 0, "rolling_30d": 0, "problems": 0},
            }
        finally:
            await conn.close()

    async def get_all_role_scores(self) -> list[dict[str, Any]]:
        conn = await asyncpg.connect(settings.database_url)
        try:
            rows = await conn.fetch(
                "SELECT * FROM role_scores ORDER BY rolling_30d_points DESC",
            )
            return [
                {
                    "role": r["role"],
                    "cumulative_points": r["cumulative_points"],
                    "rolling_30d_points": r["rolling_30d_points"],
                    "problems_contributed": r["problems_contributed"],
                    "last_updated": str(r["last_updated"]),
                }
                for r in rows
            ]
        finally:
            await conn.close()

    async def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = await asyncpg.connect(settings.database_url)
        try:
            rows = await conn.fetch(
                """SELECT id, problem_id, agent_id, role, signal, points, rationale, created_at
                   FROM reward_events ORDER BY created_at DESC LIMIT $1""",
                limit,
            )
            return [
                {
                    "id": str(r["id"]),
                    "problem_id": str(r["problem_id"]) if r["problem_id"] else None,
                    "agent_id": r["agent_id"],
                    "role": r["role"],
                    "signal": r["signal"],
                    "points": r["points"],
                    "rationale": r["rationale"],
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]
        finally:
            await conn.close()
