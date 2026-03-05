"""Tests for newly added API endpoints: judge check, current task, tool-event."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.db.connection import get_db
from api.main import app

PROB_UUID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TASK_UUID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def _override_db():
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


def test_judge_check__has_pass__returns_true(_override_db: AsyncMock):
    mock_row = {"cnt": 1}
    mock_result = MagicMock()
    mock_result.mappings.return_value.one.return_value = mock_row
    _override_db.execute = AsyncMock(return_value=mock_result)

    with TestClient(app) as c:
        resp = c.get(f"/api/judge_verdicts/check/{TASK_UUID}")
    assert resp.status_code == 200
    assert resp.json()["has_pass"] is True


def test_judge_check__no_pass__returns_false(_override_db: AsyncMock):
    mock_row = {"cnt": 0}
    mock_result = MagicMock()
    mock_result.mappings.return_value.one.return_value = mock_row
    _override_db.execute = AsyncMock(return_value=mock_result)

    with TestClient(app) as c:
        resp = c.get(f"/api/judge_verdicts/check/{TASK_UUID}")
    assert resp.status_code == 200
    assert resp.json()["has_pass"] is False


def test_tasks_current__found__returns_summary(_override_db: AsyncMock):
    mock_row = {"summary": "Build pipeline: Extract CSVs and load into PG"}
    mock_result = MagicMock()
    mock_result.mappings.return_value.one_or_none.return_value = mock_row
    _override_db.execute = AsyncMock(return_value=mock_result)

    with TestClient(app) as c:
        resp = c.get(
            f"/api/tasks/current?agent_id=agent-1&problem_id={PROB_UUID}"
        )
    assert resp.status_code == 200
    assert "Build pipeline" in resp.json()["task"]


def test_tasks_current__not_found__returns_unknown(_override_db: AsyncMock):
    mock_result = MagicMock()
    mock_result.mappings.return_value.one_or_none.return_value = None
    _override_db.execute = AsyncMock(return_value=mock_result)

    with TestClient(app) as c:
        resp = c.get(
            f"/api/tasks/current?agent_id=agent-1&problem_id={PROB_UUID}"
        )
    assert resp.status_code == 200
    assert resp.json()["task"] == "unknown task"


def test_internal_events__valid__returns_ok():
    with patch("api.main.get_event_bus") as mock_bus_fn:
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()
        mock_bus_fn.return_value = mock_bus

        with TestClient(app) as c:
            resp = c.post(
                "/internal/events",
                json={
                    "event_type": "tool_called",
                    "agent_id": "agent-1",
                    "problem_uuid": PROB_UUID,
                    "timestamp_utc": 1234567890.0,
                    "payload": {},
                },
            )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_internal_events__missing_event_type__returns_400():
    with TestClient(app) as c:
        resp = c.post("/internal/events", json={"agent_id": "agent-1"})
    assert resp.status_code == 400
    assert "event_type" in resp.json()["detail"]


def test_internal_events__invalid_json__returns_400():
    with TestClient(app) as c:
        resp = c.post(
            "/internal/events",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400
