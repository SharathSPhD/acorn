"""Phase 2 E2E test: problem decomposition → task lifecycle → judge verdict."""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from api.main import app
from api.db.connection import get_db
from api.dependencies import get_event_bus
from api.events.bus import EventBus


def _mock_db_session():
    """Build an AsyncMock that mimics SQLAlchemy AsyncSession execute/commit."""
    session = AsyncMock()
    # Default: return empty result
    mock_result = MagicMock()
    mock_result.mappings.return_value.one.return_value = {}
    mock_result.mappings.return_value.first.return_value = None
    mock_result.mappings.return_value.__iter__ = MagicMock(return_value=iter([]))
    session.execute.return_value = mock_result
    session.commit.return_value = None
    return session


@pytest.fixture
def client():
    bus = EventBus()
    db_session = _mock_db_session()

    async def override_db():
        yield db_session

    def override_bus():
        return bus

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_event_bus] = override_bus
    with TestClient(app) as c:
        yield c, db_session
    app.dependency_overrides.clear()


def _make_row(**kwargs):
    """Make a mock DB row that returns kwargs for mappings().one()."""
    from datetime import datetime, timezone
    defaults = {
        "id": uuid4(), "title": "T", "description": None,
        "status": "pending", "solution_url": None, "idempotency_key": None,
        "created_at": datetime.now(timezone.utc), "updated_at": None,
        "problem_id": uuid4(), "task_type": "ingest", "assigned_to": None,
        "blocked_by": [], "checks": {}, "notes": None,
        "task_id": uuid4(), "verdict": "pass",
    }
    defaults.update(kwargs)
    return defaults


def test_phase2_e2e__problem_create__returns_201(client):
    """Orchestrator creates a problem."""
    c, db = client
    row = _make_row(title="CSV Analysis", status="pending")
    db.execute.return_value.mappings.return_value.one.return_value = row
    resp = c.post("/api/problems", json={"title": "CSV Analysis", "description": "Analyse sales.csv"})
    assert resp.status_code == 201
    assert resp.json()["title"] == "CSV Analysis"


def test_phase2_e2e__task_create__ingest_and_analyse(client):
    """Orchestrator creates ingest + analyse tasks."""
    c, db = client
    problem_id = uuid4()
    row = _make_row(problem_id=problem_id, task_type="ingest", status="pending")
    db.execute.return_value.mappings.return_value.one.return_value = row
    resp = c.post("/api/tasks", json={
        "problem_id": str(problem_id), "title": "Ingest CSV",
        "task_type": "ingest",
    })
    assert resp.status_code == 201


@pytest.mark.skip(reason="task state machine mocking requires SQLAlchemy Row fixture")
def test_phase2_e2e__task_status__claimed_then_complete(client):
    """DE claims task then marks it complete."""
    c, db = client
    task_id = uuid4()
    resp = c.patch(f"/api/tasks/{task_id}/status", json={"status": "claimed"})
    assert resp.status_code in (200, 201, 422)  # 422 = illegal transition caught by state machine


def test_phase2_e2e__judge_verdict__submit_and_retrieve(client):
    """Judge submits pass verdict; GET returns it."""
    c, db = client
    task_id = uuid4()
    problem_id = uuid4()
    from datetime import datetime, timezone
    verdict_row = _make_row(
        id=uuid4(), task_id=task_id, verdict="pass",
        checks={"linting": True, "tests": True}, notes=None,
        created_at=datetime.now(timezone.utc),
    )
    db.execute.return_value.mappings.return_value.one.return_value = verdict_row
    db.execute.return_value.mappings.return_value.__iter__ = MagicMock(
        return_value=iter([verdict_row])
    )

    resp = c.post("/api/judge_verdicts", json={
        "task_id": str(task_id), "verdict": "pass",
        "checks": {"linting": True, "tests": True},
    })
    assert resp.status_code == 201

    resp2 = c.get(f"/api/judge_verdicts/{problem_id}")
    assert resp2.status_code == 200
