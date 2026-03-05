"""Unit tests for reward_service, manifest_engine, agent_creator, and API routers.

Covers: rewards, manifest, cortex, goals, context, tools.
All external I/O (asyncpg, httpx, redis) is mocked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


# ── RewardService ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reward_service__record_reward__known_signal__uses_default_points():
    """record_reward with known signal uses REWARD_SIGNALS value."""
    from api.services.reward_service import RewardService, REWARD_SIGNALS

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(
        return_value={"id": "ev-1", "created_at": "2025-01-01T00:00:00"}
    )
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("api.services.reward_service.asyncpg.connect", return_value=mock_conn):
        svc = RewardService()
        result = await svc.record_reward(
            signal="JUDGE_PASS",
            agent_id="agent-1",
            role="judge-agent",
        )
    assert result["points"] == REWARD_SIGNALS["JUDGE_PASS"]
    assert result["id"] == "ev-1"
    mock_conn.fetchrow.assert_called_once()
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_reward_service__record_reward__custom_points__uses_provided():
    """record_reward with explicit points uses provided value."""
    from api.services.reward_service import RewardService

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(
        return_value={"id": "ev-2", "created_at": "2025-01-01T00:00:00"}
    )
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("api.services.reward_service.asyncpg.connect", return_value=mock_conn):
        svc = RewardService()
        result = await svc.record_reward(
            signal="CUSTOM",
            agent_id="a",
            role="r",
            points=42,
        )
    assert result["points"] == 42


@pytest.mark.asyncio
async def test_reward_service__get_role_context__returns_wins_misses_score():
    """get_role_context returns recent wins, misses, and score."""
    from api.services.reward_service import RewardService

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(
        side_effect=[
            [{"signal": "JUDGE_PASS", "points": 10, "rationale": "ok", "created_at": "2025-01-01"}],
            [{"signal": "JUDGE_FAIL", "points": -5, "rationale": "bad", "created_at": "2025-01-02"}],
        ]
    )
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "cumulative_points": 100,
            "rolling_30d_points": 50,
            "problems_contributed": 5,
        }
    )
    mock_conn.close = AsyncMock()

    with patch("api.services.reward_service.asyncpg.connect", return_value=mock_conn):
        svc = RewardService()
        result = await svc.get_role_context("judge-agent")
    assert result["role"] == "judge-agent"
    assert len(result["recent_wins"]) == 1
    assert len(result["recent_misses"]) == 1
    assert result["score"]["cumulative"] == 100


@pytest.mark.asyncio
async def test_reward_service__get_all_role_scores__returns_list():
    """get_all_role_scores returns sorted role scores."""
    from api.services.reward_service import RewardService

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(
        return_value=[
            {
                "role": "r1",
                "cumulative_points": 10,
                "rolling_30d_points": 5,
                "problems_contributed": 1,
                "last_updated": "2025-01-01",
            },
        ]
    )
    mock_conn.close = AsyncMock()

    with patch("api.services.reward_service.asyncpg.connect", return_value=mock_conn):
        svc = RewardService()
        result = await svc.get_all_role_scores()
    assert len(result) == 1
    assert result[0]["role"] == "r1"


@pytest.mark.asyncio
async def test_reward_service__get_recent_events__returns_events():
    """get_recent_events returns event list."""
    from api.services.reward_service import RewardService

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(
        return_value=[
            {
                "id": "e1",
                "problem_id": "p1",
                "agent_id": "a1",
                "role": "r1",
                "signal": "S",
                "points": 10,
                "rationale": "x",
                "created_at": "2025-01-01",
            },
        ]
    )
    mock_conn.close = AsyncMock()

    with patch("api.services.reward_service.asyncpg.connect", return_value=mock_conn):
        svc = RewardService()
        result = await svc.get_recent_events(limit=20)
    assert len(result) == 1
    assert result[0]["signal"] == "S"


# ── Rewards Router ──────────────────────────────────────────────────────────


def test_rewards_router__list_events__returns_200():
    """GET /api/rewards/events returns 200."""
    with patch("api.routers.rewards.RewardService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.get_recent_events = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc

        with TestClient(app) as client:
            resp = client.get("/api/rewards/events?limit=10")
    assert resp.status_code == 200


def test_rewards_router__record__missing_signal__returns_400():
    """POST /api/rewards/record without signal returns 400."""
    with TestClient(app) as client:
        resp = client.post("/api/rewards/record", json={})
    assert resp.status_code == 400
    assert "signal" in resp.json()["detail"]


def test_rewards_router__record__valid__returns_201():
    """POST /api/rewards/record with signal returns 201."""
    with patch("api.routers.rewards.RewardService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.record_reward = AsyncMock(
            return_value={"id": "ev-1", "created_at": "2025-01-01", "points": 10}
        )
        mock_svc_cls.return_value = mock_svc

        with TestClient(app) as client:
            resp = client.post(
                "/api/rewards/record",
                json={"signal": "JUDGE_PASS", "agent_id": "a", "role": "r"},
            )
    assert resp.status_code == 201
    assert resp.json()["points"] == 10


# ── ManifestEngine ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manifest_engine__perceive__returns_desired_and_actual():
    """ManifestEngine.perceive returns desired and actual state."""
    import tempfile
    from pathlib import Path

    from api.services.manifest_engine import ManifestEngine

    manifest_content = '{"domains":{"etl":{"target_kernels":3}},"agent_catalogue":{},"model_routing":{}}'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(manifest_content)
        manifest_path = f.name

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[{"category": "etl", "cnt": 1}])
    mock_conn.close = AsyncMock()

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "qwen3-coder"}]}
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    try:
        with (
            patch("api.services.manifest_engine.asyncpg.connect", return_value=mock_conn),
            patch("api.services.manifest_engine.httpx.AsyncClient", return_value=mock_client),
        ):
            engine = ManifestEngine(manifest_path)
            result = await engine.perceive()
        assert "desired" in result
        assert "actual" in result
        assert "kernels_by_domain" in result["actual"]
    finally:
        Path(manifest_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_manifest_engine__diff__missing_kernels__returns_delta():
    """ManifestEngine.diff returns missing_kernels delta."""
    from api.services.manifest_engine import ManifestEngine

    engine = ManifestEngine("/tmp/x.json")
    desired = {"domains": {"etl": {"target_kernels": 3}}, "agent_catalogue": {}, "model_routing": {}}
    actual = {"kernels_by_domain": {"etl": 1}, "present_agents": [], "available_models": []}
    deltas = await engine.diff(desired, actual)
    assert len(deltas) >= 1
    assert any(d["type"] == "missing_kernels" for d in deltas)


@pytest.mark.asyncio
async def test_manifest_engine__diff__missing_agent__returns_delta():
    """ManifestEngine.diff returns missing_agent delta for required agent."""
    from api.services.manifest_engine import ManifestEngine

    engine = ManifestEngine("/tmp/x.json")
    desired = {
        "domains": {},
        "agent_catalogue": {"orchestrator": {"required": True}},
        "model_routing": {},
    }
    actual = {"kernels_by_domain": {}, "present_agents": [], "available_models": ["qwen"]}
    deltas = await engine.diff(desired, actual)
    assert any(d["type"] == "missing_agent" and d["agent_id"] == "orchestrator" for d in deltas)


# ── Manifest Router ────────────────────────────────────────────────────────


def test_manifest_router__status__returns_200():
    """GET /api/manifest/status returns 200."""
    with patch("api.routers.manifest.ManifestEngine") as mock_engine_cls:
        mock_engine = MagicMock()
        mock_engine.perceive = AsyncMock(
            return_value={"desired": {}, "actual": {"kernels_by_domain": {}, "available_models": [], "present_agents": []}}
        )
        mock_engine_cls.return_value = mock_engine

        with TestClient(app) as client:
            resp = client.get("/api/manifest/status")
    assert resp.status_code == 200


def test_manifest_router__deltas__returns_200():
    """GET /api/manifest/deltas returns 200."""
    with patch("api.routers.manifest.ManifestEngine") as mock_engine_cls:
        mock_engine = MagicMock()
        mock_engine.reconcile = AsyncMock(return_value=[])
        mock_engine_cls.return_value = mock_engine

        with TestClient(app) as client:
            resp = client.get("/api/manifest/deltas")
    assert resp.status_code == 200


# ── Cortex Router ───────────────────────────────────────────────────────────


def test_cortex_router__status__returns_200():
    """GET /api/cortex/status returns 200."""
    with patch("api.routers.cortex.get_cortex") as mock_get:
        mock_cortex = MagicMock()
        mock_cortex.get_status.return_value = {
            "running": False,
            "current_broadcast": None,
            "tick_interval": 120,
            "broadcast_log_size": 0,
        }
        mock_get.return_value = mock_cortex

        with TestClient(app) as client:
            resp = client.get("/api/cortex/status")
    assert resp.status_code == 200
    assert resp.json()["running"] is False


def test_cortex_router__modules__no_broadcast__returns_module_list():
    """GET /api/cortex/modules returns module list when no broadcast."""
    with patch("api.routers.cortex.get_cortex") as mock_get:
        mock_cortex = MagicMock()
        mock_cortex.current_broadcast = None
        mock_cortex.modules = [MagicMock(name="perception"), MagicMock(name="memory")]
        mock_get.return_value = mock_cortex

        with TestClient(app) as client:
            resp = client.get("/api/cortex/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_cortex_router__start__already_running__returns_already_running():
    """POST /api/cortex/start when running returns already_running."""
    with patch("api.routers.cortex.get_cortex") as mock_get:
        mock_cortex = MagicMock()
        mock_cortex.running = True
        mock_get.return_value = mock_cortex

        with TestClient(app) as client:
            resp = client.post("/api/cortex/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_running"


def test_cortex_router__stop__returns_stopped():
    """POST /api/cortex/stop returns stopped."""
    with patch("api.routers.cortex.get_cortex") as mock_get:
        mock_cortex = MagicMock()
        mock_get.return_value = mock_cortex

        with TestClient(app) as client:
            resp = client.post("/api/cortex/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


# ── AgentCreator ────────────────────────────────────────────────────────────


def test_agent_creator__create_agent__new__returns_created():
    """AgentCreator.create_agent creates new agent file."""
    import tempfile
    from pathlib import Path

    from api.services.agent_creator import AgentCreator

    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp) / "agents"
        creator = AgentCreator(str(agents_dir))
        result = creator.create_agent(
            name="test-agent",
            description="Test",
            identity="I am test",
            execute_description="Do X",
            report_description="Report Y",
            output_contract="JSON",
            constraints="None",
        )
    assert result["created"] is True
    assert "path" in result


def test_agent_creator__create_agent__exists__returns_already_exists():
    """AgentCreator.create_agent when file exists returns already_exists."""
    import tempfile
    from pathlib import Path

    from api.services.agent_creator import AgentCreator

    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp) / "agents"
        agents_dir.mkdir()
        (agents_dir / "existing.md").write_text("# existing")
        creator = AgentCreator(str(agents_dir))
        result = creator.create_agent(
            name="existing",
            description="x",
            identity="x",
            execute_description="x",
            report_description="x",
            output_contract="x",
            constraints="x",
        )
    assert result["created"] is False
    assert result["reason"] == "already_exists"


def test_agent_creator__list_agents__empty_dir__returns_empty():
    """AgentCreator.list_agents on empty dir returns []."""
    import tempfile
    from pathlib import Path

    from api.services.agent_creator import AgentCreator

    with tempfile.TemporaryDirectory() as tmp:
        creator = AgentCreator(str(Path(tmp) / "nonexistent"))
        result = creator.list_agents()
    assert result == []


def test_agent_creator__list_agents__with_files__returns_list():
    """AgentCreator.list_agents returns agent definitions."""
    import tempfile
    from pathlib import Path

    from api.services.agent_creator import AgentCreator

    with tempfile.TemporaryDirectory() as tmp:
        agents_dir = Path(tmp) / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.md").write_text("# a1")
        (agents_dir / "agent2.md").write_text("# a2")
        creator = AgentCreator(str(agents_dir))
        result = creator.list_agents()
    assert len(result) == 2
    names = {r["name"] for r in result}
    assert "agent1" in names
    assert "agent2" in names


# ── Goals Router (system-goals, create-agent, agents) ───────────────────────


def test_goals_router__system_goals__returns_goals():
    """GET /api/meta/system-goals returns goals dict."""
    mock_conn = AsyncMock()
    # fetchval: total_perm, domains_with_kernels, total_judged, passed,
    # avg_time, avg_steps, total_problems
    mock_conn.fetchval = AsyncMock(side_effect=[5, 2, 10, 8, 100.5, 4.2, 20])
    mock_conn.close = AsyncMock()

    mock_path = MagicMock()
    mock_path.exists.return_value = False  # No manifest file
    mock_path.__truediv__ = lambda self, x: mock_path

    with (
        patch("api.routers.goals.asyncpg.connect", return_value=mock_conn),
        patch("api.routers.goals.Path", return_value=mock_path),
    ):
        with TestClient(app) as client:
            resp = client.get("/api/meta/system-goals")
    assert resp.status_code == 200
    data = resp.json()
    assert "goals" in data


def test_goals_router__create_agent__returns_result():
    """POST /api/meta/create-agent creates agent."""
    with patch("api.services.agent_creator.AgentCreator") as mock_creator_cls:
        mock_creator = MagicMock()
        mock_creator.create_agent.return_value = {"created": True, "path": "/tmp/agents/new.md"}
        mock_creator_cls.return_value = mock_creator

        with TestClient(app) as client:
            resp = client.post(
                "/api/meta/create-agent",
                json={
                    "name": "new-agent",
                    "description": "d",
                    "identity": "i",
                    "execute_description": "e",
                    "report_description": "r",
                    "output_contract": "o",
                    "constraints": "c",
                },
            )
    assert resp.status_code == 200
    assert resp.json()["created"] is True


def test_goals_router__list_agents__returns_list():
    """GET /api/meta/agents returns agent list."""
    with patch("api.services.agent_creator.AgentCreator") as mock_creator_cls:
        mock_creator = MagicMock()
        mock_creator.list_agents.return_value = [{"name": "a1", "path": "/p/a1.md"}]
        mock_creator_cls.return_value = mock_creator

        with TestClient(app) as client:
            resp = client.get("/api/meta/agents")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── Context Router ──────────────────────────────────────────────────────────


def test_context_router__orient__returns_context():
    """POST /api/context/orient returns orient context."""
    with patch("api.routers.context.ContextManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.build_orient_context = AsyncMock(
            return_value={
                "relevant_episodes": [],
                "relevant_kernels": [],
                "research_hits": [],
                "domain_knowledge": [],
            }
        )
        mock_mgr_cls.return_value = mock_mgr

        with TestClient(app) as client:
            resp = client.post(
                "/api/context/orient",
                json={"description": "Build ETL", "domain": "etl"},
            )
    assert resp.status_code == 200
    assert "relevant_episodes" in resp.json()


def test_context_router__cache_research__returns_id():
    """POST /api/context/cache-research returns id."""
    with patch("api.routers.context.ContextManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.cache_research = AsyncMock(return_value="rid-123")
        mock_mgr_cls.return_value = mock_mgr

        with TestClient(app) as client:
            resp = client.post(
                "/api/context/cache-research",
                json={"query": "test", "source": "web"},
            )
    assert resp.status_code == 200
    assert resp.json()["id"] == "rid-123"


def test_context_router__store_knowledge__returns_id():
    """POST /api/context/store-knowledge returns id."""
    with patch("api.routers.context.ContextManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.store_domain_knowledge = AsyncMock(return_value="kid-456")
        mock_mgr_cls.return_value = mock_mgr

        with TestClient(app) as client:
            resp = client.post(
                "/api/context/store-knowledge",
                json={"domain": "etl", "concept": "pipeline", "description": "ETL pipeline"},
            )
    assert resp.status_code == 200
    assert resp.json()["id"] == "kid-456"


# ── Tools Router ─────────────────────────────────────────────────────────────


def test_tools_router__web_search__returns_results():
    """POST /api/tools/web-search returns search results."""
    with patch("api.routers.tools.WebSearchService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(
            return_value=[{"title": "t1", "url": "u1", "snippet": "s1"}]
        )
        mock_svc_cls.return_value = mock_svc

        with TestClient(app) as client:
            resp = client.post(
                "/api/tools/web-search",
                json={"query": "python asyncio"},
            )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["query"] == "python asyncio"


def test_tools_router__find_datasets__returns_results():
    """POST /api/tools/find-datasets returns dataset results."""
    with patch("api.routers.tools.DatasetDiscoveryService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(
            return_value=[{"id": "ds1", "description": "Dataset 1"}]
        )
        mock_svc_cls.return_value = mock_svc

        with TestClient(app) as client:
            resp = client.post(
                "/api/tools/find-datasets",
                json={"query": "nlp"},
            )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
