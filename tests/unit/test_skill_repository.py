import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from memory.kernel_repository import PostgreSQLKernelRepository
from memory.interfaces import PromotionThresholdNotMetError


@pytest.mark.asyncio
async def test_kernel_repository__find_by_keywords__returns_matching_skills():
    """find_by_keywords with query returns skills from database."""
    skill_id = uuid4()
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, key: {
        "id": skill_id,
        "name": "etl-pipeline",
        "category": "etl",
        "description": "Kernel for ETL",
        "trigger_keywords": ["pipeline", "etl"],
        "embedding": None,
        "status": "permanent",
        "use_count": 5,
        "verified_on_problems": [],
        "filesystem_path": "/skills/etl_pipeline.md",
        "deprecated_reason": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }[key]

    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetch.return_value = [mock_row]

        repo = PostgreSQLKernelRepository()
        result = await repo.find_by_keywords("pipeline", top_k=5)

        assert len(result) == 1
        assert result[0].name == "etl-pipeline"
        assert result[0].category == "etl"
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_kernel_repository__find_by_keywords__with_category__calls_category_query():
    """find_by_keywords with category filters results."""
    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetch.return_value = []

        repo = PostgreSQLKernelRepository()
        await repo.find_by_keywords("test", category="etl", top_k=5)

        # Verify the query with category was called
        calls = mock_conn.fetch.call_args_list
        assert len(calls) == 1
        query_call = calls[0][0][0]
        assert "category = $1" in query_call
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_kernel_repository__promote__below_threshold__raises_promotion_threshold_not_met():
    """promote raises PromotionThresholdNotMet when verified_on_problems < threshold."""
    skill_id = uuid4()

    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_tx = MagicMock()
        mock_tx.__aenter__ = AsyncMock(return_value=None)
        mock_tx.__aexit__ = AsyncMock(return_value=False)
        mock_conn.transaction = MagicMock(return_value=mock_tx)
        mock_conn.fetchrow.return_value = {"verified_on_problems": [uuid4()]}  # Only 1, threshold is 2

        repo = PostgreSQLKernelRepository()
        with pytest.raises(PromotionThresholdNotMetError):
            await repo.promote(skill_id)

        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_kernel_repository__promote__at_threshold__executes_update():
    """promote executes UPDATE when verified_on_problems >= threshold."""
    skill_id = uuid4()

    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_tx = MagicMock()
        mock_tx.__aenter__ = AsyncMock(return_value=None)
        mock_tx.__aexit__ = AsyncMock(return_value=False)
        mock_conn.transaction = MagicMock(return_value=mock_tx)
        mock_conn.fetchrow.return_value = {"verified_on_problems": [uuid4(), uuid4()]}  # 2 verified

        repo = PostgreSQLKernelRepository()
        await repo.promote(skill_id)

        # Verify UPDATE was called
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "UPDATE kernels SET status='permanent'" in call_args[0]
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_kernel_repository__deprecate__calls_execute_with_reason():
    """deprecate updates skill status to deprecated with reason."""
    skill_id = uuid4()
    reason = "No longer maintained"

    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn

        repo = PostgreSQLKernelRepository()
        await repo.deprecate(skill_id, reason)

        # Verify the UPDATE was called with reason
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "UPDATE kernels SET status='deprecated'" in call_args[0]
        assert reason in call_args
        mock_conn.close.assert_called_once()
