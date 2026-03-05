__pattern__ = "Repository"

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from api.services.cortex import get_cortex

router = APIRouter(prefix="/api/cortex", tags=["cortex"])


@router.get("/status")
async def cortex_status() -> dict[str, Any]:
    cortex = get_cortex()
    return cortex.get_status()


@router.get("/modules")
async def cortex_modules() -> list[dict[str, Any]]:
    cortex = get_cortex()
    if cortex.current_broadcast:
        log = cortex.get_broadcast_log(limit=1)
        if log:
            return [
                {"module": name, "salience": sal}
                for name, sal in log[-1].get("all_saliences", {}).items()
            ]
    return [{"module": m.name, "salience": 0.0} for m in cortex.modules]


@router.get("/broadcast-log")
async def cortex_broadcast_log(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    cortex = get_cortex()
    return cortex.get_broadcast_log(limit=limit)


@router.post("/start")
async def cortex_start() -> dict[str, str]:
    cortex = get_cortex()
    if cortex.running:
        return {"status": "already_running"}
    cortex._task = asyncio.create_task(cortex.run())
    return {"status": "started"}


@router.post("/stop")
async def cortex_stop() -> dict[str, str]:
    cortex = get_cortex()
    cortex.stop()
    return {"status": "stopped"}
