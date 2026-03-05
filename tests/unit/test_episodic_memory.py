"""Unit tests for episodic memory delegation layer."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from memory.interfaces import Episode


@pytest.mark.asyncio
async def test_episodic__store__delegates_to_repository():
    """PostgresEpisodicMemoryRepository.store delegates to PostgreSQLEpisodicRepository."""
    expected_id = uuid4()
    mock_delegate = MagicMock()
    mock_delegate.store = AsyncMock(return_value=expected_id)

    with patch("memory.episodic.PostgreSQLEpisodicRepository", return_value=mock_delegate):
        from memory.episodic import PostgresEpisodicMemoryRepository
        repo = PostgresEpisodicMemoryRepository(db_url="postgresql://test")

    episode = Episode(
        id=uuid4(), problem_id=uuid4(), agent_id="a1",
        event_type="test", content="test content",
    )
    result = await repo.store(episode)
    assert result == expected_id
    mock_delegate.store.assert_called_once_with(episode)


@pytest.mark.asyncio
async def test_episodic__retrieve_similar__delegates():
    """retrieve_similar forwards to delegate."""
    mock_delegate = MagicMock()
    mock_delegate.retrieve_similar = AsyncMock(return_value=[])

    with patch("memory.episodic.PostgreSQLEpisodicRepository", return_value=mock_delegate):
        from memory.episodic import PostgresEpisodicMemoryRepository
        repo = PostgresEpisodicMemoryRepository(db_url="postgresql://test")

    result = await repo.retrieve_similar([0.1, 0.2], top_k=3)
    assert result == []


@pytest.mark.asyncio
async def test_episodic__mark_retrieved__delegates():
    """mark_retrieved forwards to delegate."""
    episode_id = uuid4()
    mock_delegate = MagicMock()
    mock_delegate.mark_retrieved = AsyncMock()

    with patch("memory.episodic.PostgreSQLEpisodicRepository", return_value=mock_delegate):
        from memory.episodic import PostgresEpisodicMemoryRepository
        repo = PostgresEpisodicMemoryRepository(db_url="postgresql://test")

    await repo.mark_retrieved(episode_id)
    mock_delegate.mark_retrieved.assert_called_once_with(episode_id)
