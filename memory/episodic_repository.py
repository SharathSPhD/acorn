__pattern__ = "Repository"

from uuid import UUID

import asyncpg

from api.config import settings
from memory.interfaces import Episode, EpisodicMemoryRepository


class PostgreSQLEpisodicRepository(EpisodicMemoryRepository):
    def __init__(self, conn_str: str | None = None) -> None:
        self._conn_str = conn_str or settings.database_url

    async def store(self, episode: Episode) -> UUID:
        conn = await asyncpg.connect(self._conn_str)
        try:
            row = await conn.fetchrow(
                """INSERT INTO episodes (problem_id, agent_id, event_type, content, embedding)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                episode.problem_id, episode.agent_id, episode.event_type,
                episode.content, episode.embedding
            )
            return UUID(row["id"]) if isinstance(row["id"], str) else row["id"]
        finally:
            await conn.close()

    async def retrieve_similar(self, query_embedding: list[float], top_k: int = 5) -> list[Episode]:
        conn = await asyncpg.connect(self._conn_str)
        try:
            rows = await conn.fetch(
                """SELECT * FROM episodes
                   WHERE embedding IS NOT NULL AND archived_at IS NULL
                   ORDER BY embedding <=> $1::vector
                   LIMIT $2""",
                query_embedding, top_k
            )
            return [_row_to_episode(r) for r in rows]
        finally:
            await conn.close()

    async def retrieve_global(
        self, embedding: list[float], limit: int = 10
    ) -> list[dict[str, object]]:
        """Retrieve similar episodes across all problems."""
        conn = await asyncpg.connect(self._conn_str)
        try:
            rows = await conn.fetch(
                """SELECT id, problem_id, agent_id, event_type, content,
                          1 - (embedding <=> $1::vector) as similarity,
                          created_at
                   FROM episodes
                   WHERE embedding IS NOT NULL AND archived_at IS NULL
                   ORDER BY embedding <=> $1::vector
                   LIMIT $2""",
                embedding, limit
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async def mark_retrieved(self, episode_id: UUID) -> None:
        conn = await asyncpg.connect(self._conn_str)
        try:
            await conn.execute(
                """UPDATE episodes SET retrieved_count = retrieved_count + 1,
                   last_retrieved_at = NOW() WHERE id = $1""",
                episode_id
            )
        finally:
            await conn.close()


    async def consolidate_domain(
        self, domain: str, min_episodes: int = 20, output_path: str | None = None,
    ) -> dict[str, object]:
        """Consolidate episodic memory into kernel candidates.

        Clusters episodes by event_type. When a domain has enough episodes,
        extracts recurring patterns and writes KERNEL.md candidates to the
        probationary grove for human review and promotion.

        Returns a summary dict with extracted_count and candidate_paths.
        """
        import json
        from collections import defaultdict
        from pathlib import Path

        conn = await asyncpg.connect(self._conn_str)
        try:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM episodes WHERE archived_at IS NULL"
            ) or 0
            if count < min_episodes:
                return {"extracted_count": 0, "skipped": True, "reason": "below_threshold"}

            rows = await conn.fetch(
                """SELECT event_type, content, created_at FROM episodes
                   WHERE archived_at IS NULL
                   ORDER BY created_at DESC LIMIT 500"""
            )
        finally:
            await conn.close()

        # Group episodes by event_type (simplest clustering)
        clusters: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            clusters[row["event_type"]].append(row["content"])

        probationary = Path(output_path or settings.kernel_probationary_path)
        probationary.mkdir(parents=True, exist_ok=True)

        candidate_paths: list[str] = []
        for event_type, contents in clusters.items():
            if len(contents) < 3:  # Need at least 3 similar episodes for a pattern
                continue
            kernel_name = f"episode-pattern-{domain}-{event_type}".lower().replace("_", "-")
            kernel_path = probationary / f"{kernel_name}.md"
            if kernel_path.exists():
                continue  # Don't overwrite existing candidates

            # Summarise the pattern from recent episodes
            sample_contents = contents[:5]
            try:
                parsed = [json.loads(c) for c in sample_contents if c]
            except json.JSONDecodeError:
                parsed = [{"raw": c} for c in sample_contents]

            kernel_content = "\n".join([
                f"# Episodic Kernel Candidate: {kernel_name}",
                "",
                f"**Domain:** {domain}",
                f"**Pattern type:** {event_type}",
                f"**Episode count:** {len(contents)}",
                "",
                "## Extracted Pattern",
                "",
                "This kernel candidate was auto-extracted from episodic memory consolidation.",
                "Review and promote via `KernelRepository.promote()` after verifying on 2+ problems.",  # noqa: E501
                "",
                "## Sample Episodes",
                "",
                *[f"```json\n{json.dumps(p, indent=2)}\n```" for p in parsed[:3]],
                "",
                "## Status",
                "- [ ] Reviewed by kernel-extractor",
                "- [ ] Verified on problem 1",
                "- [ ] Verified on problem 2",
                "- [ ] Promoted to permanent grove",
            ])
            kernel_path.write_text(kernel_content)
            candidate_paths.append(str(kernel_path))

        return {
            "extracted_count": len(candidate_paths),
            "candidate_paths": candidate_paths,
            "total_episodes": count,
            "clusters_found": len(clusters),
        }


def _row_to_episode(row: asyncpg.Record) -> Episode:
    return Episode(
        id=row["id"], problem_id=row["problem_id"], agent_id=row["agent_id"],
        event_type=row["event_type"], content=row["content"],
        embedding=list(row["embedding"]) if row["embedding"] else None,
        retrieved_count=row["retrieved_count"], last_retrieved_at=row["last_retrieved_at"],
        archived_at=row["archived_at"], created_at=row["created_at"],
    )
