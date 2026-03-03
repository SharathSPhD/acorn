"""Tests for resource cap enforcement in the agent spawn endpoint."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient

PROB_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROB_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PROB_C = "cccccccc-cccc-cccc-cccc-cccccccccccc"
PROB_D = "dddddddd-dddd-dddd-dddd-dddddddddddd"


def _make_agent(problem_uuid: str, agent_id: str = "agent-1"):
    m = MagicMock()
    m.problem_uuid = problem_uuid
    m.agent_id = agent_id
    return m


def test_spawn__within_all_limits__returns_200():
    from api.main import app
    mock_registry = AsyncMock()
    mock_registry.get_all = AsyncMock(return_value=[])
    mock_registry.register = AsyncMock()
    mock_factory = MagicMock()
    mock_spec = MagicMock()
    mock_spec.agent_id = "new-agent-id"
    mock_factory.create.return_value = mock_spec
    mock_factory.launch.return_value = "container-abc"

    with patch("api.services.agent_registry.AgentRegistry", return_value=mock_registry), \
         patch("api.factories.agent_factory.DGXAgentFactory", return_value=mock_factory):
        with TestClient(app) as client:
            resp = client.post(f"/api/agents/spawn?role=coder&problem_uuid={PROB_A}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "new-agent-id"
    assert data["container_id"] == "container-abc"


def test_spawn__max_harness_containers_reached__returns_503():
    from api.main import app
    agents = [_make_agent(PROB_A, f"agent-{i}") for i in range(20)]
    mock_registry = AsyncMock()
    mock_registry.get_all = AsyncMock(return_value=agents)
    mock_registry.register = AsyncMock()

    with patch("api.services.agent_registry.AgentRegistry", return_value=mock_registry), \
         patch("api.factories.agent_factory.DGXAgentFactory"):
        with TestClient(app) as client:
            resp = client.post(f"/api/agents/spawn?role=coder&problem_uuid={PROB_B}")
    assert resp.status_code == 503
    assert "MAX_HARNESS_CONTAINERS" in resp.json()["detail"]


def test_spawn__max_agents_per_problem_reached__returns_503():
    from api.main import app
    agents = [_make_agent(PROB_A, f"agent-{i}") for i in range(10)]
    mock_registry = AsyncMock()
    mock_registry.get_all = AsyncMock(return_value=agents)
    mock_registry.register = AsyncMock()

    with patch("api.services.agent_registry.AgentRegistry", return_value=mock_registry), \
         patch("api.factories.agent_factory.DGXAgentFactory"):
        with TestClient(app) as client:
            resp = client.post(f"/api/agents/spawn?role=coder&problem_uuid={PROB_A}")
    assert resp.status_code == 503
    assert "MAX_AGENTS_PER_PROBLEM" in resp.json()["detail"]


def test_spawn__max_concurrent_problems_reached__returns_503():
    from api.main import app
    agents = [
        _make_agent(PROB_A, "agent-1"),
        _make_agent(PROB_B, "agent-2"),
        _make_agent(PROB_C, "agent-3"),
    ]
    mock_registry = AsyncMock()
    mock_registry.get_all = AsyncMock(return_value=agents)
    mock_registry.register = AsyncMock()

    with patch("api.services.agent_registry.AgentRegistry", return_value=mock_registry), \
         patch("api.factories.agent_factory.DGXAgentFactory"):
        with TestClient(app) as client:
            resp = client.post(f"/api/agents/spawn?role=coder&problem_uuid={PROB_D}")
    assert resp.status_code == 503
    assert "MAX_CONCURRENT_PROBLEMS" in resp.json()["detail"]


def test_spawn__existing_problem_at_concurrent_limit__allowed():
    from api.main import app
    agents = [
        _make_agent(PROB_A, "agent-1"),
        _make_agent(PROB_B, "agent-2"),
        _make_agent(PROB_C, "agent-3"),
    ]
    mock_registry = AsyncMock()
    mock_registry.get_all = AsyncMock(return_value=agents)
    mock_registry.register = AsyncMock()
    mock_factory = MagicMock()
    mock_spec = MagicMock()
    mock_spec.agent_id = "new-agent-id"
    mock_factory.create.return_value = mock_spec
    mock_factory.launch.return_value = "container-abc"

    with patch("api.services.agent_registry.AgentRegistry", return_value=mock_registry), \
         patch("api.factories.agent_factory.DGXAgentFactory", return_value=mock_factory):
        with TestClient(app) as client:
            resp = client.post(f"/api/agents/spawn?role=reviewer&problem_uuid={PROB_A}")
    assert resp.status_code == 200
