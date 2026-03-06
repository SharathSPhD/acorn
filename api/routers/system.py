__pattern__ = "Repository"

import asyncpg
from fastapi import APIRouter, HTTPException

from api.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health-deep", response_model=dict)
async def health_deep() -> dict:
    """Deep health check with system metrics and recommendations."""
    conn = await asyncpg.connect(settings.database_url)
    try:
        # Calculate pass rate (last 7 days)
        total_7d = await conn.fetchval(
            """SELECT COUNT(*) FROM problems
               WHERE updated_at > NOW() - INTERVAL '7 days'"""
        ) or 0
        passed_7d = await conn.fetchval(
            """SELECT COUNT(*) FROM problems
               WHERE status = 'complete'
               AND updated_at > NOW() - INTERVAL '7 days'"""
        ) or 0
        pass_rate_7d = (passed_7d / total_7d) if total_7d > 0 else 0.0

        # Active harnesses
        active_harnesses = await conn.fetchval(
            """SELECT COUNT(*) FROM problems WHERE status = 'active'"""
        ) or 0

        # Stalled problems (active > 20 minutes)
        stalled = await conn.fetch(
            """SELECT id, title, updated_at,
                      EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as stalled_minutes
               FROM problems
               WHERE status = 'active'
               AND updated_at < NOW() - INTERVAL '20 minutes'
               ORDER BY updated_at ASC"""
        )
        stalled_problems = [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "stalled_for_minutes": int(r["stalled_minutes"] or 0),
            }
            for r in stalled
        ]

        # Kernel counts
        permanent_kernels = await conn.fetchval(
            "SELECT COUNT(*) FROM kernels WHERE status = 'permanent'"
        ) or 0
        probationary_kernels = await conn.fetchval(
            "SELECT COUNT(*) FROM kernels WHERE status = 'probationary'"
        ) or 0

        # CORTEX+ status
        cortex_running = False
        try:
            from api.services.cortex import get_cortex
            cortex = get_cortex()
            cortex_running = cortex.running
        except Exception:
            pass

        # Recent failures (7 days)
        recent_failures = await conn.fetchval(
            """SELECT COUNT(*) FROM problems
               WHERE status = 'failed'
               AND updated_at > NOW() - INTERVAL '7 days'"""
        ) or 0

        # Episode count
        episode_count = await conn.fetchval("SELECT COUNT(*) FROM episodes") or 0

        # Manifest gaps
        import json
        from pathlib import Path
        manifest_gaps = 0
        try:
            manifest_path = Path(settings.acorn_root) / "manifest_domains.json"
            if manifest_path.exists():
                with manifest_path.open() as f:
                    manifest = json.load(f)
                domains = manifest.get("domains", {})
                rows = await conn.fetch(
                    """SELECT category, COUNT(*) as cnt
                       FROM kernels WHERE status IN ('permanent', 'probationary')
                       GROUP BY category"""
                )
                cat_counts = {r["category"]: r["cnt"] for r in rows}
                for domain, spec in domains.items():
                    have = cat_counts.get(domain, 0)
                    want = spec.get("target_kernels", 3)
                    if have < want:
                        manifest_gaps += want - have
        except Exception:
            pass

        # Generate recommendations
        recommendations = []
        if pass_rate_7d < 0.5:
            recommendations.append(
                f"Increase pass rate: currently {pass_rate_7d:.1%}. "
                "Review recent failures and identify common root causes."
            )
        if stalled_problems:
            recommendations.append(
                f"Force-fail {len(stalled_problems)} stalled problem(s). "
                "WARDEN will auto-fail problems active >20 min."
            )
        if permanent_kernels < 5:
            recommendations.append(
                f"Build more permanent kernels ({permanent_kernels} / 5 minimum). "
                "Complete kernel extraction and promotion workflow."
            )
        if episode_count == 0:
            recommendations.append(
                "No episodes recorded yet. Ensure problem completion calls /api/episodes."
            )
        if manifest_gaps > 3:
            recommendations.append(
                f"Close {manifest_gaps} manifest gaps. "
                "CORTEX+ will auto-spawn kernel problems for missing domains."
            )

        return {
            "pass_rate_7d": round(pass_rate_7d, 3),
            "active_harnesses": active_harnesses,
            "stalled_problems": stalled_problems,
            "permanent_kernels": permanent_kernels,
            "probationary_kernels": probationary_kernels,
            "cortex_running": cortex_running,
            "recent_failures": recent_failures,
            "episode_count": episode_count,
            "manifest_gaps": manifest_gaps,
            "recommendations": recommendations,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await conn.close()
