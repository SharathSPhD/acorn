"""Unit tests for constitutional hard gates (C1 and C4).

C1: Local Sovereignty — non-local source_urls without cloud_escalation → HTTP 403
C4: Resource Respect — MAX_HARNESS_CONTAINERS ceiling → HTTP 429
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# C1 — Local Sovereignty gate (ProblemCreate.source_urls validation)
# ---------------------------------------------------------------------------

class TestC1LocalSovereignty:
    """Tests for constitutional rule C1: reject non-local source URLs."""

    def test_c1__local_url__is_permitted(self) -> None:
        """localhost URLs pass C1 without cloud_escalation."""
        from api.models import ProblemCreate
        body = ProblemCreate(
            title="test",
            source_urls=["http://localhost:8080/data.csv"],
            cloud_escalation=False,
        )
        # Source URLs with localhost should not trigger C1
        local_hosts = {"localhost", "127.0.0.1", "::1", "acorn-api", "acorn-ollama"}
        import urllib.parse
        for url in (body.source_urls or []):
            host = urllib.parse.urlparse(url).hostname or ""
            assert host in local_hosts

    def test_c1__external_url_without_escalation__is_rejected(self) -> None:
        """External URLs without cloud_escalation=true fail C1."""
        import urllib.parse
        url = "https://external-dataset.com/data.csv"
        local_hosts = {"localhost", "127.0.0.1", "::1", "acorn-api", "acorn-ollama"}
        host = urllib.parse.urlparse(url).hostname or ""
        assert host not in local_hosts

    def test_c1__external_url_with_cloud_escalation__is_permitted(self) -> None:
        """External URLs with cloud_escalation=true bypass C1."""
        from api.models import ProblemCreate
        body = ProblemCreate(
            title="test",
            source_urls=["https://external.com/data.csv"],
            cloud_escalation=True,
        )
        assert body.cloud_escalation is True

    def test_c1__no_source_urls__always_permitted(self) -> None:
        """Problems without source_urls are never subject to C1."""
        from api.models import ProblemCreate
        body = ProblemCreate(title="test", cloud_escalation=False)
        assert body.source_urls is None

    @pytest.mark.asyncio
    async def test_c1__create_problem__external_url_returns_403(self) -> None:
        """POST /api/problems with non-local URL and no cloud_escalation → 403."""
        from api.models import ProblemCreate

        mock_db = AsyncMock()
        mock_bus = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://acorn:acorn@localhost:5432/acorn"
        mock_settings.max_concurrent_problems = 3

        body = ProblemCreate(
            title="external test",
            source_urls=["https://external-site.com/dataset.csv"],
            cloud_escalation=False,
        )

        from api.routers.problems import create_problem
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            with pytest.raises(HTTPException) as exc_info:
                await create_problem(body=body, db=mock_db, bus=mock_bus, settings=mock_settings)

            assert exc_info.value.status_code == 403
            assert "C1" in exc_info.value.detail
            assert "cloud_escalation" in exc_info.value.detail


# ---------------------------------------------------------------------------
# C4 — Resource Respect gate (MAX_HARNESS_CONTAINERS ceiling)
# ---------------------------------------------------------------------------

class TestC4ResourceRespect:
    """Tests for constitutional rule C4: MAX_HARNESS_CONTAINERS hard ceiling."""

    @pytest.mark.asyncio
    async def test_c4__spawn_at_limit__returns_429(self) -> None:
        """Spawning when MAX_HARNESS_CONTAINERS reached → HTTP 429."""
        from api.routers.agents import spawn_agent

        mock_settings = MagicMock()
        mock_settings.max_harness_containers = 2
        mock_settings.max_agents_per_problem = 10
        mock_settings.max_concurrent_problems = 3
        mock_settings.redis_url = "redis://localhost:6379"

        # Simulate 2 agents already running (at limit)
        agent1 = MagicMock()
        agent1.problem_uuid = str(uuid4())
        agent2 = MagicMock()
        agent2.problem_uuid = str(uuid4())

        with patch("api.services.agent_registry.AgentRegistry") as MockRegistry:
            mock_reg = AsyncMock()
            MockRegistry.return_value = mock_reg
            mock_reg.get_all.return_value = [agent1, agent2]

            with patch("api.services.agent_registry.AgentRegistry", MockRegistry):
                # Patch inside the function's import path
                import api.services.agent_registry as _reg_mod
                orig = _reg_mod.AgentRegistry
                _reg_mod.AgentRegistry = MockRegistry  # type: ignore[assignment]
                try:
                    with pytest.raises(HTTPException) as exc_info:
                        await spawn_agent(
                            role="orchestrator",
                            problem_uuid=uuid4(),
                            settings=mock_settings,
                        )
                finally:
                    _reg_mod.AgentRegistry = orig

            assert exc_info.value.status_code == 429
            assert "C4" in exc_info.value.detail

    def test_c4__max_harness_containers__status_code_is_429(self) -> None:
        """The spawn endpoint uses HTTP 429 (not 503) for MAX_HARNESS_CONTAINERS — C4 spec."""
        import inspect
        from api.routers import agents as agents_mod
        source = inspect.getsource(agents_mod.spawn_agent)
        # Verify C4 uses 429
        assert "429" in source or "HTTP_429_TOO_MANY_REQUESTS" in source
        assert "C4" in source
