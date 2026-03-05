"""Builder (warden) router stub. Full implementation in Phase 2+."""
__pattern__ = "Repository"

from fastapi import APIRouter

router = APIRouter(prefix="/api/builder", tags=["builder"])
