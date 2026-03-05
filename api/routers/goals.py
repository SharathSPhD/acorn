__pattern__ = "Repository"

import json
from pathlib import Path
from typing import Any

import asyncpg
from fastapi import APIRouter, Request

from api.config import settings

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/system-goals")
async def get_system_goals() -> dict[str, Any]:
    """Compute the 5 system goals from reward1.md and manifest_domains.json."""
    goals: dict[str, Any] = {}

    manifest_path = Path(settings.acorn_root) / "manifest_domains.json"
    system_goals_def: dict[str, Any] = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        system_goals_def = manifest.get("system_goals", {})

    conn = await asyncpg.connect(settings.database_url)
    try:
        total_perm = await conn.fetchval(
            "SELECT COUNT(*) FROM kernels WHERE status = 'permanent'"
        )
        domains_with_kernels = await conn.fetchval(
            """SELECT COUNT(DISTINCT category) FROM kernels
               WHERE status = 'permanent'"""
        )
        goals["G-SYS-1"] = {
            "name": "Grow kernel grove",
            "target": system_goals_def.get("G-SYS-1", {}).get(
                "target", ">=3 permanent kernels per active domain"
            ),
            "current": {
                "permanent_kernels": total_perm or 0,
                "domains_covered": domains_with_kernels or 0,
            },
        }

        total_judged = await conn.fetchval("SELECT COUNT(*) FROM judge_verdicts")
        passed = await conn.fetchval(
            "SELECT COUNT(*) FROM judge_verdicts WHERE verdict = 'pass'"
        )
        pass_rate = (passed or 0) / max(total_judged or 1, 1)
        goals["G-SYS-2"] = {
            "name": "Improve judge pass rate",
            "target": "> 0.70",
            "current": {"pass_rate": round(pass_rate, 3), "total_judged": total_judged or 0},
        }

        avg_time = await conn.fetchval(
            """SELECT EXTRACT(EPOCH FROM AVG(updated_at - created_at))
               FROM problems WHERE status = 'complete'"""
        )
        goals["G-SYS-3"] = {
            "name": "Reduce mean time to solution",
            "target": "Decrease 10% per 20 problems",
            "current": {"mean_seconds": round(avg_time or 0, 1)},
        }

        avg_steps = await conn.fetchval(
            "SELECT AVG(reasoning_steps) FROM tasks WHERE status = 'complete'"
        )
        goals["G-SYS-4"] = {
            "name": "Deepen reasoning trails",
            "target": ">=5 reasoning steps per task",
            "current": {"avg_steps": round(avg_steps or 0, 1)},
        }

        total_problems = await conn.fetchval(
            "SELECT COUNT(*) FROM problems WHERE status = 'complete'"
        )
        goals["G-SYS-5"] = {
            "name": "Reuse before reinventing",
            "target": "> 0.60 kernel reuse rate",
            "current": {
                "total_complete": total_problems or 0,
                "reuse_rate": 0.0,
            },
        }
    finally:
        await conn.close()

    return {"goals": goals}


@router.post("/create-agent")
async def create_agent(request: Request) -> dict[str, Any]:
    """Dynamically create a new agent definition."""
    from api.services.agent_creator import AgentCreator

    body = await request.json()
    creator = AgentCreator(str(Path(settings.acorn_root) / ".claude" / "agents"))
    result = creator.create_agent(
        name=body.get("name", ""),
        description=body.get("description", ""),
        identity=body.get("identity", ""),
        execute_description=body.get("execute_description", ""),
        report_description=body.get("report_description", ""),
        output_contract=body.get("output_contract", ""),
        constraints=body.get("constraints", ""),
    )
    return result


@router.get("/agents")
async def list_dynamic_agents() -> list[dict[str, str]]:
    """List all agent definitions."""
    from api.services.agent_creator import AgentCreator

    creator = AgentCreator(str(Path(settings.acorn_root) / ".claude" / "agents"))
    return creator.list_agents()
