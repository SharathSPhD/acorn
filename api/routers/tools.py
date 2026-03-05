__pattern__ = "Repository"

from typing import Any

from fastapi import APIRouter, Request

from api.services.dataset_discovery import DatasetDiscoveryService
from api.services.web_search import WebSearchService

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/web-search")
async def web_search(request: Request) -> dict[str, Any]:
    """Search the web via DuckDuckGo."""
    body = await request.json()
    query = body.get("query", "")
    max_results = body.get("max_results", 10)
    cache_results = body.get("cache_results", False)

    svc = WebSearchService()
    results = await svc.search(query, max_results=max_results, cache_results=cache_results)
    return {"query": query, "results": results, "count": len(results)}


@router.post("/find-datasets")
async def find_datasets(request: Request) -> dict[str, Any]:
    """Search for datasets on HuggingFace Hub."""
    body = await request.json()
    query = body.get("query", "")
    limit = body.get("limit", 10)

    svc = DatasetDiscoveryService()
    results = await svc.search(query, limit=limit)
    return {"query": query, "results": results, "count": len(results)}
