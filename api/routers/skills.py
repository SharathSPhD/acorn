__pattern__ = "Repository"

from uuid import UUID

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(category: str | None = None, status: str = "permanent"):
    raise HTTPException(status_code=501, detail="Phase 3: not yet implemented")


@router.post("/{skill_id}/promote")
async def promote_skill(skill_id: UUID):
    """Promote skill from probationary to permanent via SkillRepository.promote()."""
    raise HTTPException(status_code=501, detail="Phase 3: not yet implemented")
