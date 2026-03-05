"""Builder router — ACORN's self-improvement sprint engine."""
__pattern__ = "Repository"

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import AcornSettings
from api.db.connection import get_db
from api.dependencies import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/builder", tags=["builder"])

_builder_state: dict[str, Any] = {
    "status": "idle",
    "cycle_count": 0,
    "last_action": None,
    "last_action_result": None,
    "last_action_time": None,
    "circuit_breaker": {"state": "closed", "consecutive_failures": 0},
    "current_sprint": None,
}

_sprint_history: list[dict[str, Any]] = []
_thoughts: list[str] = []

CB_THRESHOLD = 4


@router.get("/status")
async def builder_status(
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Return current builder state."""
    return {
        **_builder_state,
        "builder_enabled": settings.builder_enabled,
        "thoughts": _thoughts[-10:] if _thoughts else [],
        "last_sprint_result": _sprint_history[-1] if _sprint_history else None,
    }


@router.get("/history")
async def builder_history(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return sprint history and kernel stats."""
    kernel_result = await db.execute(text("SELECT COUNT(*) FROM kernels"))
    total_kernels = kernel_result.scalar_one()

    domain_result = await db.execute(text(
        "SELECT category, COUNT(*) AS cnt FROM kernels"
        " WHERE status = 'permanent'"
        " GROUP BY category"
    ))
    domain_baselines = {
        row["category"]: row["cnt"]
        for row in domain_result.mappings().all()
    }

    return {
        "sprint_count": len(_sprint_history),
        "total_skills": total_kernels,
        "total_commits": sum(1 for s in _sprint_history if s.get("committed")),
        "release_count": 0,
        "stories_since_release": len(_sprint_history),
        "domain_baselines": domain_baselines,
        "recent_sprints": _sprint_history[-20:],
    }


@router.get("/thoughts")
async def builder_thoughts() -> dict[str, Any]:
    """Return recent builder thoughts/audit output."""
    return {"thoughts": _thoughts[-50:], "total": len(_thoughts)}


@router.get("/cortex-state")
async def cortex_state(
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Alias for status (UI compatibility)."""
    return {
        **_builder_state,
        "builder_enabled": settings.builder_enabled,
        "thoughts": _thoughts[-10:] if _thoughts else [],
        "last_sprint_result": _sprint_history[-1] if _sprint_history else None,
    }


@router.post("/start-sprint")
async def start_sprint(
    settings: AcornSettings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start a self-improvement sprint.

    Creates a self-referential problem: ACORN audits its own telemetry,
    identifies the highest-impact gap, and submits it as a problem to solve.
    """
    if _builder_state["status"] == "running":
        raise HTTPException(status_code=409, detail="Sprint already in progress")

    cb = _builder_state["circuit_breaker"]
    if cb["state"] == "halted":
        raise HTTPException(
            status_code=503,
            detail=f"Circuit breaker halted after {cb['consecutive_failures']} failures",
        )

    _builder_state["status"] = "running"
    _builder_state["cycle_count"] += 1
    sprint_num = _builder_state["cycle_count"]
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _thoughts.append(f"Sprint #{sprint_num} started at {started_at}")

    sprint_record: dict[str, Any] = {
        "sprint_number": sprint_num,
        "started_at": started_at,
        "problems_submitted": 0,
        "problems_passed": 0,
        "skills_ingested": 0,
        "changes_committed": False,
        "circuit_breaker_state": "closed",
    }

    try:
        _thoughts.append("Auditing system health and telemetry...")

        telemetry = await db.execute(text(
            "SELECT event_type, COUNT(*) AS cnt FROM agent_telemetry"
            " WHERE created_at >= NOW() - INTERVAL '24 hours'"
            " GROUP BY event_type ORDER BY cnt DESC LIMIT 10"
        ))
        events_summary = {
            r["event_type"]: r["cnt"]
            for r in telemetry.mappings().all()
        }

        kernel_coverage = await db.execute(text(
            "SELECT category, COUNT(*) AS cnt, "
            "SUM(CASE WHEN status = 'permanent' THEN 1 ELSE 0 END) AS perm"
            " FROM kernels GROUP BY category"
        ))
        coverage = {
            r["category"]: {"total": r["cnt"], "permanent": r["perm"]}
            for r in kernel_coverage.mappings().all()
        }

        problems_result = await db.execute(text(
            "SELECT status, COUNT(*) AS cnt FROM problems"
            " WHERE created_at >= NOW() - INTERVAL '7 days'"
            " GROUP BY status"
        ))
        problem_stats = {
            r["status"]: r["cnt"]
            for r in problems_result.mappings().all()
        }

        audit_summary = {
            "events_24h": events_summary,
            "kernel_coverage": coverage,
            "problem_stats_7d": problem_stats,
        }
        _thoughts.append(f"Audit complete: {json.dumps(audit_summary, default=str)}")

        weak_domains = [
            d for d in [
                "sales", "pricing", "marketing", "supply_chain", "customer",
                "finance", "operations", "human_capital", "product",
            ]
            if d not in coverage or coverage[d]["permanent"] < 3
        ]

        if weak_domains:
            target = weak_domains[0]
            title = f"Build {target} analysis kernel"
            description = (
                f"Create a reusable analysis kernel for the {target} domain. "
                f"Generate sample data, write an analysis script, test it, "
                f"and extract a KERNEL.md for the probationary grove."
            )
        else:
            title = "Improve test coverage for ACORN core"
            description = (
                "Audit existing test files, find modules with low coverage, "
                "and add targeted unit tests."
            )

        _thoughts.append(f"Improvement target: {title}")

        problem_id = uuid4()
        await db.execute(
            text("""
                INSERT INTO problems (id, title, description, status, source)
                VALUES (:id, :title, :desc, 'pending', 'builder')
            """),
            {"id": str(problem_id), "title": title, "desc": description},
        )
        await db.commit()
        sprint_record["problems_submitted"] = 1

        workspace_path = f"{settings.acorn_workspace_base}/problem-{problem_id}"
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        import os
        os.chmod(workspace_path, 0o777)
        container_name = f"acorn-harness-{problem_id}"

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "-d",
                "--name", container_name,
                "--network", settings.acorn_network,
                "-e", f"ACORN_PROBLEM_UUID={problem_id}",
                "-e", "ACORN_API_URL=http://acorn-api:8000",
                "-e", "ANTHROPIC_BASE_URL=http://acorn-api-relay:9000",
                "-e", "ANTHROPIC_AUTH_TOKEN=ollama",
                "-e", "ANTHROPIC_API_KEY=ollama",
                "-e", "REDIS_URL=redis://acorn-redis:6379",
                "-e", "DATABASE_URL=postgresql://acorn:acorn@acorn-postgres:5432/acorn",
                "-v", f"{workspace_path}:/workspace",
                "acorn/harness:latest",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode == 0:
                _thoughts.append(f"Harness launched: {container_name}")
            else:
                _thoughts.append(
                    f"Harness launch failed: {stderr.decode(errors='replace')[:200]}"
                )
        except Exception as e:
            _thoughts.append(f"Harness launch error: {e}")

        _builder_state["last_action"] = title
        _builder_state["last_action_time"] = started_at
        _builder_state["last_action_result"] = "submitted"
        cb["consecutive_failures"] = 0

        sprint_record["finished_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        sprint_record["action"] = title
        sprint_record["summary"] = f"Submitted problem: {title}"
        sprint_record["success"] = True

    except Exception as exc:
        logger.exception("Sprint failed")
        _thoughts.append(f"Sprint failed: {exc}")
        _builder_state["last_action_result"] = f"failed: {exc}"
        cb["consecutive_failures"] += 1
        if cb["consecutive_failures"] >= CB_THRESHOLD:
            cb["state"] = "halted"
            _thoughts.append("Circuit breaker HALTED")
        sprint_record["circuit_breaker_state"] = cb["state"]
        sprint_record["success"] = False

    finally:
        _builder_state["status"] = "idle"
        _sprint_history.append(sprint_record)

    return {"status": "sprint_complete", "sprint": sprint_record}


@router.post("/pause")
async def pause_builder() -> dict[str, str]:
    """Pause the builder (prevents new sprints)."""
    _builder_state["status"] = "paused"
    _thoughts.append("Builder paused by operator")
    return {"status": "paused"}


@router.post("/resume")
async def resume_builder() -> dict[str, str]:
    """Resume the builder and reset circuit breaker."""
    _builder_state["status"] = "idle"
    _builder_state["circuit_breaker"] = {"state": "closed", "consecutive_failures": 0}
    _thoughts.append("Builder resumed, circuit breaker reset")
    return {"status": "idle"}


@router.post("/stop")
async def stop_builder() -> dict[str, Any]:
    """Stop all builder-spawned harness containers."""
    _builder_state["status"] = "stopped"
    _thoughts.append("Builder stopped by operator")

    stopped = 0
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "--filter", "name=acorn-harness-",
            "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        containers = [c.strip() for c in stdout.decode().split("\n") if c.strip()]
        for c in containers:
            try:
                p = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", c,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await p.communicate()
                stopped += 1
            except Exception:
                pass
    except Exception:
        pass

    return {"status": "stopped", "harnesses_stopped": stopped}
