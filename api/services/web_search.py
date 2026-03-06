__pattern__ = "Strategy"

import asyncio
import logging
from typing import Any

from api.services.context_manager import ContextManager

logger = logging.getLogger(__name__)


class WebSearchService:
    """DuckDuckGo web search using the ddgs package."""

    async def search(
        self,
        query: str,
        max_results: int = 10,
        cache_results: bool = False,
    ) -> list[dict[str, Any]]:
        """Search using DuckDuckGo via the ddgs library."""
        results: list[dict[str, Any]] = []
        try:
            raw = await asyncio.to_thread(self._search_sync, query, max_results)
            for r in raw:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

            if results and cache_results:
                try:
                    mgr = ContextManager()
                    for r in results[:5]:
                        await mgr.cache_research(
                            query=query,
                            source="duckduckgo",
                            url=r.get("url"),
                            title=r.get("title"),
                            snippet=r.get("snippet"),
                        )
                except Exception:
                    logger.debug("Failed to cache search results")
        except Exception:
            logger.warning("Web search failed for query: %s", query, exc_info=True)
        return results

    @staticmethod
    def _search_sync(query: str, max_results: int) -> list[dict[str, Any]]:
        from ddgs import DDGS
        return list(DDGS().text(query, max_results=max_results))
