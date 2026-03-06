"""Builder's continuous learning engine — web search, dataset gathering, domain knowledge."""
__pattern__ = "Strategy"

import logging
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.services.dataset_discovery import DatasetDiscoveryService
from api.services.web_search import WebSearchService

logger = logging.getLogger(__name__)


class BuilderIntelligenceService:
    """Builder's continuous learning engine — web search, dataset gathering, domain knowledge."""

    def __init__(self) -> None:
        self.web_search = WebSearchService()
        self.dataset_discovery = DatasetDiscoveryService()

    async def research_domain(self, domain: str, db_session: AsyncSession) -> dict[str, Any]:
        """Search the web for domain knowledge, store in domain_knowledge table."""
        queries = [
            f"{domain} data analysis best practices",
            f"{domain} KPIs metrics",
            f"{domain} machine learning use cases",
        ]
        stored = 0
        learned: list[str] = []

        for query in queries:
            try:
                results = await self.web_search.search(query, max_results=5)
                for r in results:
                    content = (r.get("snippet") or r.get("title", ""))[:2000]
                    if not content:
                        continue
                    url = r.get("url", "")
                    embedding = await _get_embedding(content)
                    await _store_domain_knowledge(
                        db_session, domain, content, url, "web", embedding
                    )
                    stored += 1
                    learned.append(content[:100] + "...")
            except Exception as e:
                logger.warning("Research query failed %s: %s", query, e)

        await db_session.commit()
        return {
            "domain": domain,
            "stored": stored,
            "summary": f"Stored {stored} knowledge items. Learned: " + "; ".join(learned[:3])
            if learned
            else "No new knowledge stored.",
        }

    async def discover_datasets(
        self, domain: str, db_session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Find relevant datasets on HuggingFace for the domain."""
        datasets: list[dict[str, Any]] = []
        try:
            results = await self.dataset_discovery.search(f"{domain} dataset", limit=10)
            for ds in results:
                content = f"{ds.get('id', '')}: {ds.get('description', '')}"
                url = ds.get("url", "")
                embedding = await _get_embedding(content)
                await _store_domain_knowledge(
                    db_session, domain, content, url, "hf_model", embedding
                )
                datasets.append({
                    "id": ds.get("id"),
                    "description": ds.get("description", "")[:200],
                    "url": url,
                    "downloads": ds.get("downloads", 0),
                    "download_instructions": f"Use: huggingface-cli download {ds.get('id', '')}",
                })
            await db_session.commit()
        except Exception as e:
            logger.exception("Dataset discovery failed: %s", e)
        return datasets

    async def research_algorithms(
        self, task_type: str, domain: str, db_session: AsyncSession
    ) -> dict[str, Any]:
        """Research best algorithms for a task type in a domain."""
        queries = [
            f"{domain} {task_type} algorithm comparison",
            f"best ML model for {domain} {task_type}",
        ]
        stored = 0
        recommendations: list[str] = []

        for query in queries:
            try:
                results = await self.web_search.search(query, max_results=5)
                for r in results:
                    content = (r.get("snippet") or r.get("title", ""))[:2000]
                    if not content:
                        continue
                    url = r.get("url", "")
                    embedding = await _get_embedding(content)
                    await _store_domain_knowledge(
                        db_session, domain, content, url, "web", embedding
                    )
                    stored += 1
                    recommendations.append(content[:150] + "...")
            except Exception as e:
                logger.warning("Algorithm research failed %s: %s", query, e)

        await db_session.commit()
        return {
            "task_type": task_type,
            "domain": domain,
            "stored": stored,
            "recommendations": recommendations[:5],
        }

    async def continuous_improvement_cycle(
        self, db_session: AsyncSession
    ) -> dict[str, Any]:
        """One cycle of the builder's continuous learning."""
        summary: list[str] = []

        try:
            result = await db_session.execute(
                text("""
                    SELECT domain, COUNT(*) AS cnt
                    FROM domain_knowledge
                    GROUP BY domain
                    ORDER BY cnt ASC
                """)
            )
            rows = result.mappings().all()
            weakest_domain = rows[0]["domain"] if rows else "sales"
            summary.append(f"Weakest domain: {weakest_domain}")

            research = await self.research_domain(weakest_domain, db_session)
            summary.append(f"Research: {research.get('stored', 0)} items stored")

            datasets = await self.discover_datasets(weakest_domain, db_session)
            summary.append(f"Datasets: {len(datasets)} found")

            algo = await self.research_algorithms("analysis", weakest_domain, db_session)
            summary.append(f"Algorithms: {algo.get('stored', 0)} items stored")

            from api.services.model_intelligence import ModelIntelligenceService

            mi = ModelIntelligenceService()
            models = await mi.list_available_models()
            summary.append(f"Models synced: {len(models)}")

            sync_count = await _sync_models_from_ollama(db_session)
            summary.append(f"Registry sync: {sync_count} models")

            unbenchmarked = await _get_unbenchmarked_models(db_session)
            for name in unbenchmarked[:3]:
                try:
                    bench = await mi.benchmark_model(name)
                    swot = await mi.generate_swot(name, bench)
                    await mi.store_benchmark_results(db_session, name, bench, swot)
                    summary.append(f"Benchmarked: {name}")
                except Exception as e:
                    logger.warning("Benchmark failed for %s: %s", name, e)

            await db_session.commit()
        except Exception as e:
            logger.exception("Improvement cycle failed: %s", e)
            summary.append(f"Error: {e}")

        return {
            "cycle_complete": True,
            "summary": summary,
        }


async def _get_embedding(content: str) -> list[float] | None:
    """Generate embedding via Ollama."""
    try:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/embeddings"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json={"model": settings.embed_model, "prompt": content[:8000]},
            )
            if resp.status_code == 200:
                data = resp.json()
                emb = data.get("embedding")
                if isinstance(emb, list):
                    return [float(x) for x in emb]
    except Exception as e:
        logger.debug("Embedding failed: %s", e)
    return None


async def _store_domain_knowledge(
    db_session: AsyncSession,
    domain: str,
    content: str,
    source_url: str,
    source_type: str,
    embedding: list[float] | None,
) -> None:
    """Insert into domain_knowledge table."""
    params: dict[str, Any] = {
        "domain": domain,
        "content": content,
        "source_url": source_url or None,
        "source_type": source_type,
    }
    if embedding and len(embedding) == 768:
        emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
        await db_session.execute(
            text("""
                INSERT INTO domain_knowledge (domain, content, embedding, source_url, source_type)
                VALUES (:domain, :content, CAST(:embedding AS vector), :source_url, :source_type)
            """),
            {**params, "embedding": emb_str},
        )
    else:
        await db_session.execute(
            text("""
                INSERT INTO domain_knowledge (domain, content, source_url, source_type)
                VALUES (:domain, :content, :source_url, :source_type)
            """),
            params,
        )


async def _sync_models_from_ollama(db_session: AsyncSession) -> int:
    """Sync model_registry from Ollama /api/tags."""
    from uuid import uuid4

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            if resp.status_code != 200:
                return 0
            data = resp.json()
            models = data.get("models", [])
            for m in models:
                name = m.get("name", "")
                if not name:
                    continue
                details = m.get("details", {}) or {}
                size_bytes = details.get("size", 0) or m.get("size", 0)
                await db_session.execute(
                    text("""
                        INSERT INTO model_registry
                        (id, name, provider, size_bytes, pulled_at, is_available, updated_at)
                        VALUES (:id, :name, 'ollama', :size_bytes, NOW(), TRUE, NOW())
                        ON CONFLICT (name) DO UPDATE SET
                            size_bytes = EXCLUDED.size_bytes,
                            pulled_at = NOW(),
                            is_available = TRUE,
                            updated_at = NOW()
                    """),
                    {"id": str(uuid4()), "name": name, "size_bytes": size_bytes},
                )
            return len(models)
    except Exception as e:
        logger.warning("Model sync failed: %s", e)
        return 0


async def _get_unbenchmarked_models(db_session: AsyncSession) -> list[str]:
    """Return model names that have not been benchmarked recently."""
    result = await db_session.execute(
        text("""
            SELECT name FROM model_registry
            WHERE is_available = TRUE
              AND (last_benchmarked_at IS NULL OR last_benchmarked_at < NOW() - INTERVAL '7 days')
            ORDER BY name
        """)
    )
    return [r["name"] for r in result.mappings().all()]
