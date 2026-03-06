__pattern__ = "Repository"

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, status

from api.config import settings
from api.models import EpisodeCreate, EpisodeResponse
from memory.episodic_repository import PostgreSQLEpisodicRepository

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.post("", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(body: EpisodeCreate) -> EpisodeResponse:
    """Record an episode from problem completion."""
    conn = await asyncpg.connect(settings.database_url)
    try:
        # Generate embedding for the summary
        embedding = None
        if body.summary:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "http://acorn-ollama:11434/api/embeddings",
                        json={"model": settings.embed_model, "prompt": body.summary[:8000]},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        emb = data.get("embedding")
                        if isinstance(emb, list):
                            embedding = [float(x) for x in emb]
            except Exception:
                pass  # Embedding generation is optional

        row = await conn.fetchrow(
            """INSERT INTO episodes
               (problem_id, agent_id, event_type, content, embedding, importance)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING id, problem_id, agent_id, event_type, importance, created_at""",
            UUID(body.problem_id) if isinstance(body.problem_id, str) else body.problem_id,
            "system",
            "problem_completion",
            body.summary or "",
            embedding,
            0.7,
        )
        return EpisodeResponse(
            id=str(row["id"]),
            problem_id=str(row["problem_id"]),
            agent_id=row["agent_id"],
            event_type=row["event_type"],
            importance=row["importance"],
            created_at=str(row["created_at"]),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await conn.close()


@router.get("/count", response_model=dict[str, int])
async def get_episode_count() -> dict[str, int]:
    """Return total episode count."""
    conn = await asyncpg.connect(settings.database_url)
    try:
        count = await conn.fetchval("SELECT COUNT(*) FROM episodes") or 0
        return {"count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await conn.close()


@router.post("/consolidate", status_code=200)
async def consolidate_episodes(
    body: dict[str, str] | None = None,
) -> dict[str, object]:
    """Consolidate episodic memory into kernel candidates.

    Called by WARDEN after every N problems complete.
    """
    body = body or {}
    domain = body.get("domain", "all")  # type: ignore
    repo = PostgreSQLEpisodicRepository()
    result = await repo.consolidate_domain(domain)
    return result
