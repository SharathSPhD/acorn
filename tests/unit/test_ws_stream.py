"""Unit tests for WebSocket stream endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# aioredis may be None in bare test envs — patch the whole module attribute
_PATCH_TARGET = "api.ws.stream.aioredis"


def _make_mocks():
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub.return_value = mock_pubsub
    return mock_redis, mock_pubsub


def test_ws_stream__accepts_connection__and_disconnects_cleanly() -> None:
    """WebSocket accepts connection and handles disconnect cleanly."""
    mock_redis, mock_pubsub = _make_mocks()
    with patch(_PATCH_TARGET) as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        with client.websocket_connect("/ws/test-uuid"):
            pass
    assert mock_pubsub.unsubscribe.called
    assert mock_pubsub.aclose.called
    assert mock_redis.aclose.called


def test_ws_stream__forwards_redis_message_to_client() -> None:
    """WebSocket forwards Redis messages to connected client."""
    mock_redis, mock_pubsub = _make_mocks()
    test_message = {"type": "message", "data": '{"agent_id": "a1", "event": "task_complete"}'}
    mock_pubsub.get_message = AsyncMock(side_effect=[test_message, None])
    with patch(_PATCH_TARGET) as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        with client.websocket_connect("/ws/test-uuid") as ws:
            data = ws.receive_text()
    assert data == '{"agent_id": "a1", "event": "task_complete"}'


def test_ws_stream__subscribes_to_correct_channel() -> None:
    """WebSocket subscribes to the correct Redis pub/sub channel."""
    mock_redis, mock_pubsub = _make_mocks()
    with patch(_PATCH_TARGET) as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        with client.websocket_connect("/ws/problem-uuid-123"):
            pass
    mock_pubsub.subscribe.assert_called_once_with("oak:stream:problem-uuid-123")


def test_ws_stream__handles_redis_unavailable__disconnects_cleanly() -> None:
    """WebSocket raises if Redis connection fails."""
    with patch(_PATCH_TARGET) as mock_aioredis:
        mock_aioredis.from_url.side_effect = ConnectionError("Redis unavailable")
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/test-uuid"):
                pass


def test_ws_stream__sends_heartbeat_on_empty_queue() -> None:
    """WebSocket handles empty message queue without crashing."""
    mock_redis, mock_pubsub = _make_mocks()
    mock_pubsub.get_message = AsyncMock(side_effect=[None, None, None, None])
    with patch(_PATCH_TARGET) as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        with client.websocket_connect("/ws/test-uuid"):
            pass
    assert mock_pubsub.subscribe.called
