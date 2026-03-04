"""Tests for concurrent problem isolation and atomic skill promotion."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

PROB_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROB_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def test_agent_registry__keys_scoped_per_agent__no_cross_problem_leakage():
    """Registry stores problem_uuid per agent; filtering gives per-problem isolation."""
    import asyncio, json, time
    from api.services.agent_registry import AgentRegistry

    mock_redis = AsyncMock()
    agent_a = {"agent_id": "agent-a", "role": "coder", "problem_uuid": PROB_A,
                "status": "running", "container_id": "c-a", "last_seen": time.time()}
    agent_b = {"agent_id": "agent-b", "role": "coder", "problem_uuid": PROB_B,
                "status": "running", "container_id": "c-b", "last_seen": time.time()}

    mock_redis.keys = AsyncMock(return_value=["oak:agent:agent-a", "oak:agent:agent-b"])
    mock_redis.get = AsyncMock(side_effect=[json.dumps(agent_a), json.dumps(agent_b)])

    registry = AgentRegistry("redis://localhost:6379")
    registry._redis = mock_redis

    all_agents = asyncio.get_event_loop().run_until_complete(registry.get_all())

    agents_prob_a = [a for a in all_agents if a.problem_uuid == PROB_A]
    agents_prob_b = [a for a in all_agents if a.problem_uuid == PROB_B]

    assert len(agents_prob_a) == 1
    assert len(agents_prob_b) == 1
    assert agents_prob_a[0].agent_id == "agent-a"
    assert agents_prob_b[0].agent_id == "agent-b"


@pytest.mark.asyncio
async def test_promote__uses_for_update__prevents_double_promotion():
    """promote() uses SELECT ... FOR UPDATE inside a transaction to prevent races."""
    from memory.skill_repository import PostgreSQLSkillRepository

    skill_id = uuid4()
    mock_conn = AsyncMock()
    mock_tx = MagicMock()
    mock_tx.__aenter__ = AsyncMock(return_value=None)
    mock_tx.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_tx)  # sync call → async CM
    mock_conn.fetchrow = AsyncMock(return_value={"verified_on_problems": ["prob1", "prob2"]})
    mock_conn.execute = AsyncMock()

    with patch("memory.skill_repository.asyncpg") as mock_asyncpg, \
         patch("memory.skill_repository.settings") as mock_settings:
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
        mock_settings.oak_skill_promo_threshold = 2

        repo = PostgreSQLSkillRepository("postgresql://localhost/oak")
        await repo.promote(skill_id)

    fetchrow_call = mock_conn.fetchrow.call_args
    assert "FOR UPDATE" in fetchrow_call[0][0]
    mock_conn.transaction.assert_called_once()
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_promote__threshold_not_met__raises_and_does_not_update():
    """promote() under threshold raises PromotionThresholdNotMet and never calls UPDATE."""
    from memory.skill_repository import PostgreSQLSkillRepository
    from memory.interfaces import PromotionThresholdNotMetError

    skill_id = uuid4()
    mock_conn = AsyncMock()
    mock_tx = MagicMock()
    mock_tx.__aenter__ = AsyncMock(return_value=None)
    mock_tx.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_tx)  # sync call → async CM
    mock_conn.fetchrow = AsyncMock(return_value={"verified_on_problems": ["prob1"]})
    mock_conn.execute = AsyncMock()

    with patch("memory.skill_repository.asyncpg") as mock_asyncpg, \
         patch("memory.skill_repository.settings") as mock_settings:
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
        mock_settings.oak_skill_promo_threshold = 2

        repo = PostgreSQLSkillRepository("postgresql://localhost/oak")
        with pytest.raises(PromotionThresholdNotMetError):
            await repo.promote(skill_id)

    mock_conn.execute.assert_not_called()
