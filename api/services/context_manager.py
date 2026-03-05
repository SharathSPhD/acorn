__pattern__ = "Strategy"

import logging
from typing import Any

import asyncpg

from api.config import settings

logger = logging.getLogger(__name__)


class ContextManager:
    """
    MemOS Tier 3 Context Manager.

    Queries episodes, kernels, and research cache to build enriched
    context for agent ORIENT steps.
    """

    async def build_orient_context(
        self,
        problem_description: str,
        domain: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Build enriched context from all Tier 3 memory sources."""
        context: dict[str, Any] = {
            "relevant_episodes": [],
            "relevant_kernels": [],
            "research_hits": [],
            "domain_knowledge": [],
        }

        conn = await asyncpg.connect(settings.database_url)
        try:
            episodes = await conn.fetch(
                """SELECT id, problem_id, agent_id, event_type, content,
                          created_at
                   FROM episodes
                   ORDER BY created_at DESC
                   LIMIT 10"""
            )
            context["relevant_episodes"] = [
                {
                    "id": str(r["id"]),
                    "problem_id": str(r["problem_id"]) if r["problem_id"] else None,
                    "role": r["agent_id"],
                    "action": r["event_type"][:200] if r["event_type"] else "",
                    "outcome": r["content"][:200] if r["content"] else "",
                }
                for r in episodes
            ]

            kernel_query = """
                SELECT id, name, description, category, trigger_keywords, status
                FROM kernels
                WHERE status IN ('permanent', 'probationary')
                ORDER BY
                    CASE WHEN status = 'permanent' THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT 10
            """
            kernels = await conn.fetch(kernel_query)
            context["relevant_kernels"] = [
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "description": r["description"][:200] if r["description"] else "",
                    "category": r["category"],
                    "status": r["status"],
                }
                for r in kernels
            ]

            try:
                research = await conn.fetch(
                    """SELECT id, query, source, title, snippet
                       FROM research_cache_entries
                       ORDER BY created_at DESC
                       LIMIT 5"""
                )
                context["research_hits"] = [
                    {
                        "id": str(r["id"]),
                        "query": r["query"],
                        "source": r["source"],
                        "title": r["title"],
                        "snippet": r["snippet"][:200] if r["snippet"] else "",
                    }
                    for r in research
                ]
            except Exception:
                logger.debug("research_cache_entries query failed (table may not exist)")

            try:
                dk = await conn.fetch(
                    """SELECT id, domain, content
                       FROM domain_knowledge
                       ORDER BY created_at DESC
                       LIMIT 5"""
                )
                context["domain_knowledge"] = [
                    {
                        "id": str(r["id"]),
                        "domain": r["domain"],
                        "concept": "",
                        "description": r["content"][:200] if r["content"] else "",
                    }
                    for r in dk
                ]
            except Exception:
                logger.debug("domain_knowledge query failed (table may not exist)")

        finally:
            await conn.close()

        return context

    async def cache_research(
        self,
        query: str,
        source: str,
        url: str | None = None,
        title: str | None = None,
        snippet: str | None = None,
        content: str | None = None,
    ) -> str:
        """Cache a research result in research_cache_entries table."""
        conn = await asyncpg.connect(settings.database_url)
        try:
            row = await conn.fetchrow(
                """INSERT INTO research_cache_entries (query, source, url, title, snippet, content)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING id""",
                query, source, url, title, snippet, content,
            )
            return str(row["id"])
        finally:
            await conn.close()

    async def store_domain_knowledge(
        self,
        domain: str,
        concept: str,
        description: str,
    ) -> str:
        """Store a piece of domain knowledge."""
        conn = await asyncpg.connect(settings.database_url)
        try:
            content = f"{concept}: {description}" if concept else description
            row = await conn.fetchrow(
                """INSERT INTO domain_knowledge (domain, content)
                   VALUES ($1, $2)
                   RETURNING id""",
                domain, content,
            )
            return str(row["id"])
        finally:
            await conn.close()
