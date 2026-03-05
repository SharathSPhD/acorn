__pattern__ = "Repository"

import uuid as uuid_mod
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query

from api.config import settings
from memory.interfaces import PromotionThresholdNotMetError
from memory.kernel_repository import PostgreSQLKernelRepository, _row_to_kernel

router = APIRouter(prefix="/api/kernels", tags=["kernels"])


@router.get("")
async def list_kernels(
    query: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    top_k: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    repo = PostgreSQLKernelRepository()
    try:
        if query:
            kernels_list = await repo.find_by_keywords(query, category=category, top_k=top_k)
        else:
            conn = await asyncpg.connect(settings.database_url)
            try:
                params: list[object] = []
                q = "SELECT * FROM kernels WHERE 1=1"
                if status and status != "all":
                    params.append(status)
                    q += f" AND status = ${len(params)}"
                if category:
                    params.append(category)
                    q += f" AND category = ${len(params)}"
                q += f" ORDER BY use_count DESC LIMIT {top_k}"
                rows = await conn.fetch(q, *params)
                kernels_list = [_row_to_kernel(r) for r in rows]
            finally:
                await conn.close()
        return [
            {
                "id": str(s.id), "name": s.name, "category": s.category,
                "description": s.description, "trigger_keywords": s.trigger_keywords,
                "status": s.status, "use_count": s.use_count,
                "verified_on_problems": [str(p) for p in s.verified_on_problems],
                "filesystem_path": s.filesystem_path,
                "created_at": getattr(s, "created_at", None),
            }
            for s in kernels_list
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("")
async def create_kernel(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new probationary kernel."""
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    description = body.get("description", "")
    category = body.get("category", "general")
    keywords = body.get("trigger_keywords", [])
    problem_id = body.get("problem_id")

    skill_id = uuid_mod.uuid4()
    conn = await asyncpg.connect(settings.database_url)
    try:
        verified = [problem_id] if problem_id else []
        await conn.execute(
            """
            INSERT INTO kernels (id, name, description, category,
                trigger_keywords, status, verified_on_problems)
            VALUES ($1, $2, $3, $4, $5, 'probationary', $6)
            ON CONFLICT (name) DO UPDATE SET
                use_count = kernels.use_count + 1,
                verified_on_problems = array_cat(
                    kernels.verified_on_problems,
                    $6::uuid[]
                )
            """,
            skill_id, name, description, category,
            keywords, verified,
        )
        return {"id": str(skill_id), "name": name, "status": "probationary"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await conn.close()


@router.post("/{kernel_id}/promote")
async def promote_kernel(kernel_id: UUID) -> dict[str, str]:
    repo = PostgreSQLKernelRepository()
    try:
        await repo.promote(kernel_id)
        return {"status": "promoted", "kernel_id": str(kernel_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PromotionThresholdNotMetError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest-workspace/{problem_id}")
async def ingest_workspace_kernels(problem_id: str) -> dict[str, Any]:
    """Scan a problem workspace for KERNEL.md files and ingest as probationary kernels."""
    safe_id = Path(problem_id).name
    if safe_id != problem_id:
        raise HTTPException(status_code=400, detail="Invalid problem_id")
    workspace = Path(settings.acorn_workspace_base) / safe_id
    if not workspace.exists():
        workspace = Path(settings.acorn_workspace_base) / f"self-build-{problem_id[:8]}"
    if not workspace.exists():
        raise HTTPException(status_code=404, detail=f"Workspace not found for {problem_id}")

    skill_files = list(workspace.rglob("SKILL.md")) + list(workspace.rglob("skill.md"))
    if not skill_files:
        return {"ingested": 0, "message": "No SKILL.md files found"}

    ingested = 0
    conn = await asyncpg.connect(settings.database_url)
    try:
        for sf in skill_files:
            content = sf.read_text()
            name, description, category, keywords = _parse_skill_md(content)
            if not name:
                continue

            kernel_id = uuid_mod.uuid4()
            await conn.execute(
                """
                INSERT INTO kernels (id, name, description, category,
                    trigger_keywords, status, filesystem_path)
                VALUES ($1, $2, $3, $4, $5, 'probationary', $6)
                ON CONFLICT (name) DO NOTHING
                """,
                kernel_id, name, description, category,
                keywords, str(sf),
            )
            ingested += 1
    finally:
        await conn.close()

    return {"ingested": ingested, "files_scanned": len(skill_files)}


def _parse_skill_md(content: str) -> tuple[str, str, str, list[str]]:
    """Extract name, description, category, and keywords from a SKILL.md file."""
    lines = content.strip().split("\n")
    name = ""
    description = ""
    category = "general"
    keywords: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not name:
            name = stripped[2:].strip()
        elif stripped.lower().startswith("category:"):
            category = stripped.split(":", 1)[1].strip().lower()
        elif stripped.lower().startswith("keywords:"):
            kw_str = stripped.split(":", 1)[1].strip()
            keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
        elif stripped and not description and not stripped.startswith("#"):
            description = stripped

    return name, description, category, keywords
