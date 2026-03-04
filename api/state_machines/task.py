__pattern__ = "StateMachine"

from collections.abc import Callable
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING  = "pending"
    CLAIMED  = "claimed"
    COMPLETE = "complete"
    FAILED   = "failed"


# Adjacency map: key is current state; value is set of legal next states.
TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING:  {TaskStatus.CLAIMED, TaskStatus.FAILED},
    TaskStatus.CLAIMED:  {TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.PENDING},
    TaskStatus.COMPLETE: set(),   # Terminal
    TaskStatus.FAILED:   {TaskStatus.PENDING},  # Retry
}


class IllegalTransitionError(Exception):
    pass


class TaskStateMachine:
    def __init__(
        self,
        initial: TaskStatus,
        on_transition: Callable[[TaskStatus, TaskStatus], None] | None = None,
    ) -> None:
        self._state = initial
        self._on_transition = on_transition

    @property
    def state(self) -> TaskStatus:
        return self._state

    def transition(self, to: TaskStatus) -> None:
        if to not in TASK_TRANSITIONS[self._state]:
            raise IllegalTransitionError(
                f"Cannot move task from {self._state} to {to}")
        prev = self._state
        self._state = to
        if self._on_transition:
            self._on_transition(prev, to)
