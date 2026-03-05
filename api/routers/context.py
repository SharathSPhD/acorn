__pattern__ = "Repository"

from typing import Any

from fastapi import APIRouter, Request

from api.services.context_manager import ContextManager

router = APIRouter(prefix="/api/context", tags=["context"])


@router.post("/orient")
async def build_orient_context(request: Request) -> dict[str, Any]:
    """Build ORIENT context from MemOS Tier 3 memory sources."""
    body = await request.json()
    mgr = ContextManager()
    return await mgr.build_orient_context(
        problem_description=body.get("description", ""),
        domain=body.get("domain"),
        role=body.get("role"),
    )


@router.post("/cache-research")
async def cache_research(request: Request) -> dict[str, str]:
    """Cache a research result."""
    body = await request.json()
    mgr = ContextManager()
    rid = await mgr.cache_research(
        query=body.get("query", ""),
        source=body.get("source", "web"),
        url=body.get("url"),
        title=body.get("title"),
        snippet=body.get("snippet"),
        content=body.get("content"),
    )
    return {"id": rid}


@router.post("/store-knowledge")
async def store_knowledge(request: Request) -> dict[str, str]:
    """Store domain knowledge."""
    body = await request.json()
    mgr = ContextManager()
    kid = await mgr.store_domain_knowledge(
        domain=body.get("domain", "general"),
        concept=body.get("concept", ""),
        description=body.get("description", ""),
    )
    return {"id": kid}
