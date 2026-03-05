__pattern__ = "Repository"

import asyncio
import logging
import os
import shutil
import time
import urllib.parse
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import AcornSettings
from api.db.connection import get_db
from api.dependencies import get_event_bus, get_settings
from api.events.bus import AgentEvent, EventBus
from api.factories.agent_factory import ResourceCapExceededError, get_agent_factory
from api.models import (
    ProblemCreate,
    ProblemResponse,
    ProblemStartResponse,
    ProblemStatusUpdate,
    SpawnAgentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.post("", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    body: ProblemCreate,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
    settings: AcornSettings = Depends(get_settings),
) -> ProblemResponse:
    """Create a new problem. Returns 429 if MAX_CONCURRENT_PROBLEMS exceeded."""
    # C1: Local Sovereignty — reject non-local source_urls unless cloud_escalation=true
    _local_hosts = {"localhost", "127.0.0.1", "::1", "acorn-api", "acorn-ollama"}
    if body.source_urls and not body.cloud_escalation:
        for url in body.source_urls:
            host = urllib.parse.urlparse(url).hostname or ""
            if host and host not in _local_hosts:
                try:
                    import asyncpg
                    _conn = await asyncpg.connect(settings.database_url)
                    try:
                        await _conn.execute(
                            """INSERT INTO constitutional_violations
                               (rule, detail, source_agent)
                               VALUES ('C1', $1, 'api')""",
                            f"Non-local URL rejected: {url}",
                        )
                    finally:
                        await _conn.close()
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"C1 Local Sovereignty violation: non-local URL '{url}' "
                        "is not permitted. Set cloud_escalation=true to allow."
                    ),
                )

    active_count = await db.execute(
        text("SELECT count(*) FROM problems WHERE status IN ('active', 'assembling')"),
    )
    if active_count.scalar_one() >= settings.max_concurrent_problems:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max concurrent problems ({settings.max_concurrent_problems}) exceeded",
        )
    problem_id = uuid4()
    result = await db.execute(
        text("""
            INSERT INTO problems
            (id, title, description, status, source, idempotency_key)
            VALUES (:id, :title, :description, 'pending', :source, :idempotency_key)
            RETURNING id, title, description, status, source, solution_url,
            idempotency_key, created_at, updated_at
        """),
        {
            "id": str(problem_id),
            "title": body.title,
            "description": body.description,
            "source": body.source,
            "idempotency_key": body.idempotency_key,
        },
    )
    await db.commit()
    row = result.mappings().one()
    await bus.publish(AgentEvent(
        event_type="problem_created",
        agent_id="system",
        problem_uuid=str(problem_id),
        timestamp_utc=time.time(),
        payload={"title": body.title},
    ))
    return ProblemResponse(**dict(row))


@router.get("", response_model=list[ProblemResponse])
async def list_problems(
    db: AsyncSession = Depends(get_db),
) -> list[ProblemResponse]:
    """List all problems, newest first."""
    result = await db.execute(
        text("""
            SELECT id, title, description, status, source, solution_url,
            idempotency_key, created_at, updated_at
            FROM problems ORDER BY created_at DESC LIMIT 100
        """),
    )
    rows = result.mappings().all()
    return [ProblemResponse(**dict(r)) for r in rows]


@router.post("/cleanup")
async def cleanup_stale_problems(
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Find active/assembling problems whose harness containers have exited and mark as failed."""
    result = await db.execute(
        text("SELECT id, status FROM problems WHERE status IN ('active', 'assembling')"),
    )
    rows = result.mappings().all()
    cleaned = 0

    for row in rows:
        container_name = f"acorn-harness-{row['id']}"
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "--format", "{{.State.Running}}", container_name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            running = stdout.decode().strip().lower()
            if running != "true":
                await db.execute(
                    text(
                        "UPDATE problems SET status = 'failed',"
                        " updated_at = NOW() WHERE id = :id"
                    ),
                    {"id": str(row["id"])},
                )
                cleaned += 1
        except Exception:
            await db.execute(
                text(
                    "UPDATE problems SET status = 'failed',"
                    " updated_at = NOW() WHERE id = :id"
                ),
                {"id": str(row["id"])},
            )
            cleaned += 1

    await db.commit()
    return {"cleaned": cleaned, "total_checked": len(rows)}


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProblemResponse:
    """Get problem by ID."""
    result = await db.execute(
        text("""
            SELECT id, title, description, status, source, solution_url,
            idempotency_key, created_at, updated_at
            FROM problems WHERE id = :id
        """),
        {"id": str(problem_id)},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return ProblemResponse(**dict(row))


@router.post("/{problem_id}/start", response_model=ProblemStartResponse)
async def start_problem(
    problem_id: UUID,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
    settings: AcornSettings = Depends(get_settings),
) -> ProblemStartResponse:
    """Start the agent pipeline for a problem. Creates worktree + launches harness."""
    result = await db.execute(
        text("SELECT id, status FROM problems WHERE id = :id"),
        {"id": str(problem_id)},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    if row["status"] not in ("pending", "failed"):
        raise HTTPException(status_code=409, detail=f"Problem is already {row['status']}")

    workspace_path = f"{settings.acorn_workspace_base}/problem-{problem_id}"
    container_name = f"acorn-harness-{problem_id}"

    await db.execute(
        text("UPDATE problems SET status = 'active', updated_at = NOW() WHERE id = :id"),
        {"id": str(problem_id)},
    )
    await db.commit()

    Path(workspace_path).mkdir(parents=True, exist_ok=True)
    os.chmod(workspace_path, 0o777)

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", settings.acorn_root, "worktree", "add", "-b",
            f"acorn/problem-{problem_id}", workspace_path, "main",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            logger.warning(
                "git worktree add exited %d: %s", proc.returncode, stderr.decode(errors="replace"),
            )
    except Exception:
        logger.exception("Failed to create git worktree for problem %s", problem_id)

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
    except Exception:
        logger.debug("Container %s did not exist or could not be removed", container_name)

    # Write ORIENT_CONTEXT.md for the orchestrator's GRS reward context
    try:
        from api.services.agent_creator import AgentCreator
        creator = AgentCreator(f"{settings.acorn_root}/.claude/agents")
        await creator.write_orient_context("orchestrator", workspace_path)
    except Exception:
        logger.debug("ORIENT context write failed (non-blocking)")

    factory = get_agent_factory()
    spec = factory.create(
        role="orchestrator",
        problem_uuid=str(problem_id),
        container_name=container_name,
    )
    spec.network = settings.acorn_network
    spec.workspace_path = workspace_path

    try:
        await factory.launch(spec)
    except ResourceCapExceededError as e:
        raise HTTPException(status_code=500, detail=f"Failed to start harness: {e}") from e

    await bus.publish(AgentEvent(
        event_type="problem_started",
        agent_id="system",
        problem_uuid=str(problem_id),
        timestamp_utc=time.time(),
        payload={"container": container_name},
    ))

    return ProblemStartResponse(
        id=problem_id,
        status="active",
        container_name=container_name,
        workspace_path=workspace_path,
        message=f"Pipeline started in container {container_name}",
    )


@router.post("/{problem_id}/spawn-agent", status_code=201)
async def spawn_agent(
    problem_id: UUID,
    body: SpawnAgentRequest,
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, str]:
    """Spawn a specialist agent container for a specific role."""
    workspace_path = f"{settings.acorn_workspace_base}/problem-{problem_id}"
    suffix = str(body.task_id)[:8] if body.task_id else str(uuid4())[:8]
    container_name = f"acorn-{body.role}-{suffix}"

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
    except Exception:
        logger.debug("Old container %s not present, continuing", container_name)

    # Write role-specific ORIENT_CONTEXT.md before launching
    try:
        from api.services.agent_creator import AgentCreator
        creator = AgentCreator(f"{settings.acorn_root}/.claude/agents")
        await creator.write_orient_context(body.role, workspace_path)
    except Exception:
        logger.debug("ORIENT context write failed for role=%s (non-blocking)", body.role)

    factory = get_agent_factory()
    kwargs: dict[str, str] = {"container_name": container_name}
    if body.task_id:
        kwargs["task_id"] = body.task_id
    spec = factory.create(role=body.role, problem_uuid=str(problem_id), **kwargs)
    spec.network = settings.acorn_network
    spec.workspace_path = workspace_path

    try:
        container_id = await factory.launch(spec)
    except ResourceCapExceededError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to spawn {body.role}: {e}"
        ) from e

    return {
        "container_name": container_name,
        "container_id": container_id,
        "role": body.role,
        "model": spec.model,
    }


@router.post("/{problem_id}/upload")
async def upload_file(
    problem_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, object]:
    """Upload a data file to the problem workspace."""
    result = await db.execute(
        text("SELECT id FROM problems WHERE id = :id"),
        {"id": str(problem_id)},
    )
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    workspace_path = Path(f"{settings.acorn_workspace_base}/problem-{problem_id}")
    workspace_path.mkdir(parents=True, exist_ok=True)

    fname = Path(file.filename or "uploaded_file").name
    dest = (workspace_path / fname).resolve()
    if not str(dest).startswith(str(workspace_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    content = await file.read()
    dest.write_bytes(content)

    return {"filename": fname, "size": len(content), "path": str(dest)}


@router.get("/{problem_id}/logs")
async def get_logs(problem_id: UUID) -> dict[str, str]:
    """Get harness container logs for a problem."""
    container_name = f"acorn-harness-{problem_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", "100", container_name,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return {"container": container_name, "logs": stdout.decode(errors="replace")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{problem_id}/status")
async def get_problem_status(problem_id: UUID) -> dict[str, str]:
    """Get harness container status for a problem."""
    container_name = f"acorn-harness-{problem_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "--filter", f"name={container_name}",
            "--format", "{{.Status}}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        container_status = stdout.decode().strip() or "not found"
        return {"container": container_name, "container_status": container_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{problem_id}/files")
async def list_workspace_files(
    problem_id: UUID,
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, object]:
    """List files in the problem workspace."""
    workspace_path = Path(f"{settings.acorn_workspace_base}/problem-{problem_id}")
    if not workspace_path.exists():
        return {"files": [], "workspace": str(workspace_path)}
    files = []
    for f in sorted(workspace_path.rglob("*")):
        if f.is_file() and ".git" not in f.parts:
            files.append({
                "name": str(f.relative_to(workspace_path)),
                "size": f.stat().st_size,
            })
    return {"files": files, "workspace": str(workspace_path)}


@router.get("/{problem_id}/files/{filename:path}")
async def get_file_content(
    problem_id: UUID,
    filename: str,
    settings: AcornSettings = Depends(get_settings),
) -> FileResponse:
    """Serve a file from the problem workspace (markdown, images, code, etc)."""
    workspace = Path(f"{settings.acorn_workspace_base}/problem-{problem_id}")
    filepath = (workspace / filename).resolve()
    if not str(filepath).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)


@router.patch("/{problem_id}", response_model=ProblemResponse)
async def update_problem_status(
    problem_id: UUID,
    body: ProblemStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProblemResponse:
    """Update problem status (e.g. mark as failed, complete, archived)."""
    result = await db.execute(
        text("""
            UPDATE problems SET status = :status, updated_at = NOW()
            WHERE id = :id
            RETURNING id, title, description, status, solution_url,
            idempotency_key, created_at, updated_at
        """),
        {"id": str(problem_id), "status": body.status.value},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    await db.commit()
    return ProblemResponse(**dict(row))


@router.get("/{problem_id}/reasoning-trail")
async def get_reasoning_trail(
    problem_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Return all reasoning steps for a problem, ordered chronologically."""
    result = await db.execute(
        text("SELECT id FROM problems WHERE id = :id"),
        {"id": str(problem_id)},
    )
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    steps = await db.execute(
        text("""
            SELECT id, agent_id, step_type, summary, confidence, sources, created_at
            FROM reasoning_steps
            WHERE problem_id = :pid
            ORDER BY created_at
        """),
        {"pid": str(problem_id)},
    )
    rows = [dict(r) for r in steps.mappings().all()]
    for r in rows:
        r["id"] = str(r["id"])
        r["created_at"] = str(r["created_at"])
    return {"problem_id": str(problem_id), "steps": rows, "count": len(rows)}


@router.post("/{problem_id}/reasoning-steps", status_code=201)
async def add_reasoning_step(
    problem_id: UUID,
    body: dict[str, object],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Record a reasoning step from an agent. Used by harness entrypoint."""
    result = await db.execute(
        text("SELECT id FROM problems WHERE id = :id"),
        {"id": str(problem_id)},
    )
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    import json as _json

    agent_id = str(body.get("agent_id", "unknown"))
    step_type = str(body.get("step_type", "generic"))
    summary = str(body.get("summary", ""))
    confidence = body.get("confidence")
    sources = body.get("sources", [])

    if not summary:
        raise HTTPException(status_code=400, detail="summary is required")

    row = await db.execute(
        text("""
            INSERT INTO reasoning_steps
            (problem_id, agent_id, step_type, summary, confidence, sources)
            VALUES (:pid, :aid, :stype, :summary, :conf, CAST(:sources AS jsonb))
            RETURNING id, created_at
        """),
        {
            "pid": str(problem_id),
            "aid": agent_id,
            "stype": step_type,
            "summary": summary,
            "conf": float(str(confidence)) if confidence is not None else None,
            "sources": _json.dumps(sources if isinstance(sources, list) else []),
        },
    )
    await db.commit()
    inserted = row.mappings().one()
    return {"id": str(inserted["id"]), "created_at": str(inserted["created_at"])}


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem(
    problem_id: UUID,
    db: AsyncSession = Depends(get_db),
    settings: AcornSettings = Depends(get_settings),
) -> None:
    """Hard-delete a problem and stop its harness container if running."""
    result = await db.execute(
        text("SELECT id FROM problems WHERE id = :id"),
        {"id": str(problem_id)},
    )
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    container_name = f"acorn-harness-{problem_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
    except Exception:
        logger.debug("Container %s cleanup skipped", container_name)

    workspace_path = f"{settings.acorn_workspace_base}/problem-{problem_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "worktree", "remove", "--force", workspace_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
    except Exception:
        logger.debug("Worktree %s cleanup skipped", workspace_path)
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "branch", "-D", f"acorn/problem-{problem_id}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
    except Exception:
        logger.debug("Branch acorn/problem-%s cleanup skipped", problem_id)
    shutil.rmtree(workspace_path, ignore_errors=True)

    await db.execute(text("DELETE FROM tasks WHERE problem_id = :id"), {"id": str(problem_id)})
    await db.execute(text("DELETE FROM mailbox WHERE problem_id = :id"), {"id": str(problem_id)})
    await db.execute(
        text("DELETE FROM agent_telemetry WHERE problem_id = :id"), {"id": str(problem_id)},
    )
    await db.execute(text("DELETE FROM problems WHERE id = :id"), {"id": str(problem_id)})
    await db.commit()
