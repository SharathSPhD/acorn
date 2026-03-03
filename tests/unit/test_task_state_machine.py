"""Unit tests for TaskStateMachine."""
import pytest
from api.state_machines.task import TaskStateMachine, TaskStatus, IllegalTransitionError


def test_task_state_machine__pending_to_claimed__succeeds():
    sm = TaskStateMachine(TaskStatus.PENDING)
    sm.transition(TaskStatus.CLAIMED)
    assert sm.state == TaskStatus.CLAIMED


def test_task_state_machine__claimed_to_complete__succeeds():
    sm = TaskStateMachine(TaskStatus.CLAIMED)
    sm.transition(TaskStatus.COMPLETE)
    assert sm.state == TaskStatus.COMPLETE


def test_task_state_machine__claimed_to_failed__succeeds():
    sm = TaskStateMachine(TaskStatus.CLAIMED)
    sm.transition(TaskStatus.FAILED)
    assert sm.state == TaskStatus.FAILED


def test_task_state_machine__pending_to_complete_direct__raises_illegal_transition():
    sm = TaskStateMachine(TaskStatus.PENDING)
    with pytest.raises(IllegalTransitionError):
        sm.transition(TaskStatus.COMPLETE)


def test_task_state_machine__complete_to_any__raises_illegal_transition():
    sm = TaskStateMachine(TaskStatus.COMPLETE)
    with pytest.raises(IllegalTransitionError):
        sm.transition(TaskStatus.CLAIMED)


def test_task_state_machine__failed_to_pending__succeeds():
    """FAILED is a retryable state — transition back to PENDING is allowed."""
    sm = TaskStateMachine(TaskStatus.FAILED)
    sm.transition(TaskStatus.PENDING)
    assert sm.state == TaskStatus.PENDING
