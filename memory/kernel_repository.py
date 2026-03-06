__pattern__ = "Repository"

from uuid import UUID

import asyncpg

from api.config import settings
from memory.interfaces import Kernel, KernelRepository, PromotionThresholdNotMetError


class PostgreSQLKernelRepository(KernelRepository):
    """PostgreSQL-backed KernelRepository with pgvector similarity search."""

    def __init__(self, conn_str: str | None = None) -> None:
        self._conn_str = conn_str or settings.database_url

    async def find_by_keywords(
        self, query: str, category: str | None = None, top_k: int = 5
    ) -> list[Kernel]:
        """Match kernels whose trigger_keywords or name overlap any word in the query.

        Splits the query into individual words so that a full problem title like
        "CORTEX+ objective: pricing kernels" still matches kernels with trigger
        keywords like ["pricing", "price_elasticity"].
        """
        words = [w.lower() for w in query.replace(":", " ").replace("+", " ").split() if len(w) >= 3]
        if not words:
            words = [query.lower()]
        patterns = [f"%{w}%" for w in words]
        conn = await asyncpg.connect(self._conn_str)
        try:
            if category:
                rows = await conn.fetch(
                    """SELECT * FROM kernels
                       WHERE status != 'deprecated'
                         AND category = $1
                         AND (
                           EXISTS(SELECT 1 FROM unnest(trigger_keywords) kw
                                  WHERE kw ILIKE ANY($2::text[]))
                           OR name ILIKE ANY($2::text[])
                         )
                       LIMIT $3""",
                    category, patterns, top_k
                )
            else:
                rows = await conn.fetch(
                    """SELECT * FROM kernels
                       WHERE status != 'deprecated'
                         AND (
                           EXISTS(SELECT 1 FROM unnest(trigger_keywords) kw
                                  WHERE kw ILIKE ANY($1::text[]))
                           OR name ILIKE ANY($1::text[])
                         )
                       LIMIT $2""",
                    patterns, top_k
                )
            return [_row_to_kernel(r) for r in rows]
        finally:
            await conn.close()

    async def promote(self, kernel_id: UUID) -> None:
        conn = await asyncpg.connect(self._conn_str)
        try:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT verified_on_problems FROM kernels WHERE id = $1 FOR UPDATE",
                    kernel_id,
                )
                if row is None:
                    raise ValueError(f"Kernel {kernel_id} not found")
                threshold = settings.acorn_kernel_promo_threshold
                verified = row["verified_on_problems"] or []
                if len(verified) < threshold:
                    raise PromotionThresholdNotMetError(
                        f"Need {threshold} verified problems, have {len(verified)}"
                    )
                await conn.execute(
                    "UPDATE kernels SET status='permanent', updated_at=NOW() WHERE id=$1",
                    kernel_id,
                )
        finally:
            await conn.close()

    async def deprecate(self, kernel_id: UUID, reason: str) -> None:
        conn = await asyncpg.connect(self._conn_str)
        try:
            await conn.execute(
                """UPDATE kernels SET status='deprecated', deprecated_reason=$1,
                   updated_at=NOW() WHERE id=$2""",
                reason, kernel_id
            )
        finally:
            await conn.close()


def _row_to_kernel(row: asyncpg.Record) -> Kernel:
    from uuid import UUID as _UUID
    return Kernel(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        description=row["description"],
        trigger_keywords=list(row["trigger_keywords"] or []),
        embedding=list(row["embedding"]) if row["embedding"] else None,
        status=row["status"],
        use_count=row["use_count"],
        verified_on_problems=[_UUID(str(u)) for u in (row["verified_on_problems"] or [])],
        filesystem_path=row["filesystem_path"],
        deprecated_reason=row["deprecated_reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
