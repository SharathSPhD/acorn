__pattern__ = "Strategy"

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DatasetDiscoveryService:
    """Discover datasets from HuggingFace Hub (no API key required for public datasets)."""

    HF_API = "https://huggingface.co/api/datasets"

    async def search(
        self,
        query: str,
        limit: int = 10,
        sort: str = "downloads",
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    self.HF_API,
                    params={"search": query, "limit": limit, "sort": sort},
                )
                if resp.status_code != 200:
                    logger.warning("HuggingFace API returned %d", resp.status_code)
                    return results

                datasets = resp.json()
                for ds in datasets:
                    results.append({
                        "id": ds.get("id", ""),
                        "description": ds.get("description", "")[:200],
                        "downloads": ds.get("downloads", 0),
                        "likes": ds.get("likes", 0),
                        "tags": ds.get("tags", [])[:10],
                        "url": f"https://huggingface.co/datasets/{ds.get('id', '')}",
                    })
        except Exception:
            logger.warning("Dataset search failed for: %s", query, exc_info=True)
        return results
