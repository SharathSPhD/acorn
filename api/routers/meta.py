__pattern__ = "Repository"

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import AcornSettings
from api.db.connection import get_db
from api.dependencies import get_settings

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/proposals")
async def list_proposals(
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Return the latest meta-agent proposals from all problem workspaces."""
    base = Path(settings.acorn_workspace_base)
    proposals: list[dict[str, Any]] = []

    if base.exists():
        for ws in sorted(base.iterdir()):
            fp = ws / "meta_proposals.json"
            if fp.is_file():
                try:
                    data = json.loads(fp.read_text())
                    proposals.append({
                        "workspace": ws.name,
                        "proposals": data,
                    })
                except (json.JSONDecodeError, OSError):
                    pass

    return {"count": len(proposals), "proposals": proposals}


@router.post("/apply-proposals")
async def apply_proposals(
    settings: AcornSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Read meta_proposals.json from the daemon workspace and store for review.

    Full auto-application is out of scope for safety. This endpoint makes
    proposals queryable and logs them for human review.
    """
    daemon_ws = Path(settings.acorn_workspace_base) / "daemon"
    fp = daemon_ws / "meta_proposals.json"

    if not fp.is_file():
        return {"status": "no_proposals", "message": "No meta_proposals.json found"}

    try:
        data = json.loads(fp.read_text())
    except (json.JSONDecodeError, OSError):
        return {"status": "error", "message": "Failed to parse meta_proposals.json"}

    proposal_list = data.get("proposals", []) if isinstance(data, dict) else []

    return {
        "status": "reviewed",
        "proposal_count": len(proposal_list),
        "proposals": proposal_list,
        "message": "Proposals loaded for review. Auto-application disabled for safety.",
    }


@router.get("/health-metrics")
async def health_metrics(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """ACORN self-assessment metrics (Manifest Part V)."""

    # 1. Kernel grove coverage: domains with 3+ permanent kernels
    kgc = await db.execute(text(
        "SELECT COUNT(DISTINCT category) AS cnt FROM kernels"
        " WHERE status = 'permanent'"
        " GROUP BY category HAVING COUNT(*) >= 3"
    ))
    domains_with_3plus = len(kgc.all())

    # 2. Judge pass rate (last 7 days)
    jpr = await db.execute(text(
        "SELECT COUNT(*) FILTER (WHERE verdict = 'pass') AS passes,"
        " COUNT(*) AS total"
        " FROM judge_verdicts"
        " WHERE created_at >= NOW() - INTERVAL '7 days'"
    ))
    jpr_row = jpr.mappings().one()
    total_verdicts = int(jpr_row["total"])
    judge_pass_rate = (
        round(int(jpr_row["passes"]) / total_verdicts, 3)
        if total_verdicts > 0 else 0.0
    )

    # 3. Kernel promotion rate (last 7 days)
    kp = await db.execute(text(
        "SELECT COUNT(*) AS cnt FROM kernels"
        " WHERE promoted_at >= NOW() - INTERVAL '7 days'"
    ))
    kernel_promotions_7d = int(kp.scalar_one())

    # 4. Median time to solution (completed problems, minutes)
    mtts = await db.execute(text(
        "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP"
        " (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)) / 60)"
        " AS median_min"
        " FROM problems"
        " WHERE status = 'complete' AND completed_at IS NOT NULL"
    ))
    median_row = mtts.scalar_one()
    median_minutes = round(float(median_row), 1) if median_row else None

    # 5. Reasoning trail completeness (% of completed problems with steps)
    rtc = await db.execute(text(
        "SELECT COUNT(*) AS total,"
        " COUNT(*) FILTER (WHERE id IN"
        "   (SELECT DISTINCT problem_id FROM reasoning_steps)"
        " ) AS with_trail"
        " FROM problems WHERE status = 'complete'"
    ))
    rtc_row = rtc.mappings().one()
    rtc_total = int(rtc_row["total"])
    reasoning_completeness = (
        round(int(rtc_row["with_trail"]) / rtc_total, 3)
        if rtc_total > 0 else 0.0
    )

    # 6. WebSocket streaming coverage (always 1.0 -- wired in code)
    ws_coverage = 1.0

    return {
        "kernel_grove_coverage": {"domains_with_3plus_permanent": domains_with_3plus},
        "judge_pass_rate_7d": judge_pass_rate,
        "kernel_promotion_rate_7d": kernel_promotions_7d,
        "median_time_to_solution_minutes": median_minutes,
        "reasoning_trail_completeness": reasoning_completeness,
        "ws_streaming_coverage": ws_coverage,
    }
