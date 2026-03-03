__pattern__ = "StateMachine"

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from api.models import TaskCreate, TaskResponse
from api.state_machines.task import TaskStateMachine, TaskStatus, IllegalTransitionError

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate):
    raise HTTPException(status_code=501, detail="Phase 2: not yet implemented")


@router.patch("/{task_id}/status")
async def update_task_status(task_id: UUID, new_status: TaskStatus):
    """Transition task status via StateMachine -- illegal transitions return 422."""
    raise HTTPException(status_code=501, detail="Phase 2: not yet implemented")
