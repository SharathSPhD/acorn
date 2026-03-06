__pattern__ = "Repository"

import time
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import AcornSettings
from api.db.connection import get_db
from api.dependencies import get_settings

router = APIRouter(prefix="/api/models", tags=["models"])

# Standard benchmark prompts for model evaluation
_BENCHMARK_PROMPTS = [
    {"capability": "coding", "prompt": "Write a Python function that computes the nth Fibonacci number using recursion. Include a docstring."},
    {"capability": "analysis", "prompt": "Summarize the key differences between supervised and unsupervised machine learning in 2-3 sentences."},
    {"capability": "reasoning", "prompt": "If all A are B, and some B are C, can we conclude that some A are C? Explain your reasoning."},
]


def _row_to_model(row: Any) -> dict[str, Any]:
    """Convert a DB row to a model dict."""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    for k in ("id", "created_at", "updated_at", "last_benchmarked_at", "pulled_at"):
        if k in d and d[k] is not None and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


@router.get("")
async def list_models(
    capability: str | None = Query(default=None),
    available: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all models in registry with optional filters."""
    q = "SELECT * FROM model_registry WHERE 1=1"
    params: dict[str, Any] = {}
    if capability is not None:
        q += " AND :capability = ANY(capabilities)"
        params["capability"] = capability
    if available is not None:
        q += " AND is_available = :available"
        params["available"] = available
    q += " ORDER BY name"
    result = await db.execute(text(q), params)
    return [_row_to_model(r) for r in result.mappings()]


@router.get("/recommend")
async def recommend_model(
    task_type: str = Query(...),
    role: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Recommend best model for task_type and role based on benchmark scores and success rate."""
    result = await db.execute(
        text("""
            SELECT * FROM model_registry
            WHERE is_available = TRUE
              AND name NOT LIKE '%embed%'
              AND (benchmark_scores IS NOT NULL AND benchmark_scores != '{}')
              AND COALESCE(
                    (benchmark_scores->>'coding')::float +
                    (benchmark_scores->>'analysis')::float +
                    (benchmark_scores->>'reasoning')::float, 0
                  ) > 0
            ORDER BY
              CASE WHEN :role = ANY(recommended_roles) THEN 0 ELSE 1 END,
              COALESCE((benchmark_scores->>:task_type)::float, 0) DESC,
              success_rate DESC,
              avg_tokens_per_sec DESC NULLS LAST
            LIMIT 1
        """),
        {"role": role, "task_type": task_type},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No available model recommended for role={role} and task_type={task_type}",
        )
    return _row_to_model(row)


@router.get("/{name}")
async def get_model(
    name: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get model details including SWOT."""
    result = await db.execute(
        text("SELECT * FROM model_registry WHERE name = :name"),
        {"name": name},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return _row_to_model(row)


@router.post("/sync")
async def sync_models(
    db: AsyncSession = Depends(get_db),
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Sync with Ollama: fetch /api/tags and upsert each model into registry."""
    ollama_url = settings.ollama_base_url or "http://acorn-ollama:11434"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{ollama_url}/api/tags")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama /api/tags returned {resp.status_code}: {resp.text[:200]}",
        )
    data = resp.json()
    models = data.get("models", [])
    upserted = 0
    for m in models:
        model_info = m.get("details", {}) or {}
        name = m.get("name", "")
        if not name:
            continue
        size_bytes = model_info.get("size", 0) or m.get("size")
        await db.execute(
            text("""
                INSERT INTO model_registry (id, name, provider, size_bytes, pulled_at, is_available, updated_at)
                VALUES (:id, :name, 'ollama', :size_bytes, NOW(), TRUE, NOW())
                ON CONFLICT (name) DO UPDATE SET
                    size_bytes = EXCLUDED.size_bytes,
                    pulled_at = NOW(),
                    is_available = TRUE,
                    updated_at = NOW()
            """),
            {"id": str(uuid4()), "name": name, "size_bytes": size_bytes},
        )
        upserted += 1
    await db.commit()
    return {"synced": upserted, "models": [m.get("name", "") for m in models if m.get("name")]}


def _do_pull_sync(ollama_url: str, name: str) -> None:
    """Synchronous pull for background task."""
    with httpx.Client(timeout=3600) as client:
        client.post(f"{ollama_url}/api/pull", json={"name": name})


@router.post("/{name}/pull")
async def pull_model(
    name: str,
    background_tasks: BackgroundTasks,
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, str]:
    """Pull a model via Ollama. Returns immediately; pull runs in background."""
    ollama_url = settings.ollama_base_url or "http://acorn-ollama:11434"
    background_tasks.add_task(_do_pull_sync, ollama_url, name)
    return {"status": "accepted", "message": f"Pull of '{name}' started in background"}


@router.post("/{name}/benchmark")
async def benchmark_model(
    name: str,
    db: AsyncSession = Depends(get_db),
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Run benchmark: send standard prompts via relay, measure latency, store results."""
    relay_url = settings.anthropic_base_url.rstrip("/")
    scores: dict[str, float] = {}
    latencies: list[float] = []
    total_tokens = 0

    from api.services.model_intelligence import (
        _score_coding, _score_analysis, _score_reasoning,
        _score_instruction_following,
    )
    _cap_scorers = {
        "coding": _score_coding,
        "analysis": _score_analysis,
        "reasoning": _score_reasoning,
        "instruction_following": _score_instruction_following,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        for item in _BENCHMARK_PROMPTS:
            cap, prompt = item["capability"], item["prompt"]
            body = {
                "model": "claude-sonnet-4-6",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.anthropic_auth_token}",
                "anthropic-version": "2023-06-01",
                "x-acorn-model": name,
            }
            t0 = time.perf_counter()
            resp = await client.post(f"{relay_url}/v1/messages", json=body, headers=headers)
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            if resp.status_code == 200:
                try:
                    j = resp.json()
                    usage = j.get("usage", {}) or {}
                    out_tokens = usage.get("output_tokens", 0)
                    total_tokens += out_tokens
                    # Simple quality heuristic: non-empty response = 1.0, empty = 0.0
                    content = (j.get("content", []) or [{}])[0]
                    text_val = content.get("text", "") if isinstance(content, dict) else ""
                    scorer = _cap_scorers.get(cap)
                    quality = scorer(text_val) if scorer and text_val else (1.0 if text_val and len(text_val) > 10 else 0.5)
                    scores[cap] = round(quality, 2)
                except Exception:
                    scores[cap] = 0.0
            else:
                scores[cap] = 0.0

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    avg_tps = total_tokens / (avg_latency / 1000) if avg_latency > 0 else 0.0

    import json as _json
    scores_json = _json.dumps(scores)
    await db.execute(
        text("""
            INSERT INTO model_registry (id, name, provider, benchmark_scores, avg_latency_ms,
                avg_tokens_per_sec, last_benchmarked_at, is_available, updated_at)
            VALUES (:id, :name, 'ollama', CAST(:scores AS jsonb), :avg_latency_ms,
                :avg_tokens_per_sec, NOW(), TRUE, NOW())
            ON CONFLICT (name) DO UPDATE SET
                benchmark_scores = CAST(:scores AS jsonb),
                avg_latency_ms = :avg_latency_ms,
                avg_tokens_per_sec = :avg_tokens_per_sec,
                last_benchmarked_at = NOW(),
                updated_at = NOW()
        """),
        {
            "id": str(uuid4()),
            "name": name,
            "scores": scores_json,
            "avg_latency_ms": avg_latency,
            "avg_tokens_per_sec": avg_tps,
        },
    )
    await db.commit()

    return {
        "model": name,
        "benchmark_scores": scores,
        "avg_latency_ms": round(avg_latency, 2),
        "avg_tokens_per_sec": round(avg_tps, 2),
    }


@router.patch("/{name}/swot")
async def update_swot(
    name: str,
    body: dict[str, str],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update SWOT analysis fields for a model."""
    allowed = {"strengths", "weaknesses", "opportunities", "threats"}
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid SWOT fields provided")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["name"] = name
    result = await db.execute(
        text(f"""
            UPDATE model_registry SET {set_clause}, updated_at = NOW()
            WHERE name = :name
            RETURNING name
        """),
        updates,
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    await db.commit()
    return {"status": "updated", "model": name}


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    name: str,
    db: AsyncSession = Depends(get_db),
    settings: AcornSettings = Depends(get_settings),
) -> None:
    """Remove model from Ollama and mark as unavailable in registry."""
    ollama_url = settings.ollama_base_url or "http://acorn-ollama:11434"
    async with httpx.AsyncClient(timeout=60) as client:
        await client.request("DELETE", f"{ollama_url}/api/delete", json={"name": name})

    await db.execute(
        text("""
            UPDATE model_registry SET is_available = FALSE, updated_at = NOW()
            WHERE name = :name
        """),
        {"name": name},
    )
    await db.commit()
