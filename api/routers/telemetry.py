__pattern__ = "Observer"

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("")
async def get_telemetry():
    """Return aggregated telemetry metrics."""
    raise HTTPException(status_code=501, detail="Phase 2: not yet implemented")
