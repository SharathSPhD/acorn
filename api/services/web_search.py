__pattern__ = "Strategy"

import logging
from typing import Any

import httpx

from api.services.context_manager import ContextManager

logger = logging.getLogger(__name__)


class WebSearchService:
    """DuckDuckGo-based web search service (no API key required)."""

    DDG_URL = "https://html.duckduckgo.com/html/"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        cache_results: bool = False,
    ) -> list[dict[str, Any]]:
        """Search using DuckDuckGo HTML interface and parse results."""
        results: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.post(
                    self.DDG_URL,
                    data={"q": query},
                    headers={"User-Agent": "ACORN-Research/1.0"},
                )
                if resp.status_code != 200:
                    logger.warning("DDG returned %d", resp.status_code)
                    return results

                html = resp.text
                results = self._parse_ddg_html(html, max_results)

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

    def _parse_ddg_html(self, html: str, max_results: int) -> list[dict[str, Any]]:
        """Extract search results from DuckDuckGo HTML response."""
        import re

        results: list[dict[str, Any]] = []
        link_pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(links[:max_results]):
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_snippet = ""
            if i < len(snippets):
                clean_snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()

            if url.startswith("//duckduckgo.com/l/?uddg="):
                from urllib.parse import unquote
                url = unquote(url.split("uddg=")[1].split("&")[0])

            results.append({
                "title": clean_title,
                "url": url,
                "snippet": clean_snippet,
            })

        return results
