"""Unit tests for api.events.bus EventBus and subscriber dispatch."""
import time
from unittest.mock import AsyncMock, patch

import pytest

from api.events.bus import (
    AgentEvent,
    EpisodicMemorySubscriber,
    EventBus,
    EventSubscriber,
    SessionStateSubscriber,
    TelemetrySubscriber,
    WebSocketSubscriber,
)


class _CountingSubscriber(EventSubscriber):
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    async def on_event(self, event: AgentEvent) -> None:
        self.events.append(event)


class _FailingSubscriber(EventSubscriber):
    async def on_event(self, event: AgentEvent) -> None:
        raise RuntimeError("boom")


def _make_event(event_type: str = "test") -> AgentEvent:
    return AgentEvent(
        event_type=event_type,
        agent_id="agent-1",
        problem_uuid="p-1",
        payload={},
        timestamp_utc=time.time(),
    )


def test_event_bus__subscribe__adds_subscriber():
    bus = EventBus()
    sub = _CountingSubscriber()
    bus.subscribe(sub)
    assert len(bus._subscribers) == 1


@pytest.mark.asyncio
async def test_event_bus__publish__delivers_to_subscriber():
    bus = EventBus()
    sub = _CountingSubscriber()
    bus.subscribe(sub)
    await bus.publish(_make_event())
    assert len(sub.events) == 1


@pytest.mark.asyncio
async def test_event_bus__publish__delivers_to_multiple():
    bus = EventBus()
    s1, s2 = _CountingSubscriber(), _CountingSubscriber()
    bus.subscribe(s1)
    bus.subscribe(s2)
    await bus.publish(_make_event())
    assert len(s1.events) == 1
    assert len(s2.events) == 1


@pytest.mark.asyncio
async def test_event_bus__publish__failing_subscriber_doesnt_block():
    bus = EventBus()
    s1 = _FailingSubscriber()
    s2 = _CountingSubscriber()
    bus.subscribe(s1)
    bus.subscribe(s2)
    await bus.publish(_make_event())
    assert len(s2.events) == 1


@pytest.mark.asyncio
async def test_telemetry_subscriber__on_event__ignores_unknown_type():
    sub = TelemetrySubscriber()
    event = _make_event(event_type="unknown_type")
    await sub.on_event(event)


def test_agent_event__creation():
    e = _make_event("tool_called")
    assert e.event_type == "tool_called"
    assert e.agent_id == "agent-1"


@pytest.mark.asyncio
async def test_telemetry_subscriber__tool_called__writes_to_db():
    sub = TelemetrySubscriber()
    event = _make_event("tool_called")
    event.payload = {"tool_name": "read", "tool_input": {"path": "/a"}}

    mock_conn = AsyncMock()
    with patch("asyncpg.connect", return_value=mock_conn):
        await sub.on_event(event)

    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_telemetry_subscriber__db_failure__does_not_raise():
    sub = TelemetrySubscriber()
    event = _make_event("tool_called")

    with patch("asyncpg.connect", side_effect=RuntimeError("no db")):
        await sub.on_event(event)  # should not raise


@pytest.mark.asyncio
async def test_websocket_subscriber__publishes_to_redis():
    pytest.importorskip("redis")
    sub = WebSocketSubscriber()
    event = _make_event("task_complete")
    event.problem_uuid = "prob-123"

    mock_redis = AsyncMock()
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        await sub.on_event(event)

    mock_redis.publish.assert_called_once()
    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_subscriber__empty_uuid__skips():
    sub = WebSocketSubscriber()
    event = _make_event("task_complete")
    event.problem_uuid = ""
    await sub.on_event(event)  # should return early without touching Redis


@pytest.mark.asyncio
async def test_episodic_subscriber__ignores_non_episode_events():
    sub = EpisodicMemorySubscriber()
    event = _make_event("tool_called")
    await sub.on_event(event)  # should return early


@pytest.mark.asyncio
async def test_episodic_subscriber__task_complete__writes():
    sub = EpisodicMemorySubscriber()
    event = _make_event("task_complete")
    event.payload = {"result": "done"}

    mock_conn = AsyncMock()
    with patch("asyncpg.connect", return_value=mock_conn), \
         patch.object(sub, "_generate_embedding", return_value=None):
        await sub.on_event(event)

    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_session_subscriber__agent_spawned__registers():
    sub = SessionStateSubscriber()
    event = _make_event("agent_spawned")
    event.payload = {"role": "data-engineer"}

    mock_registry = AsyncMock()
    with patch("api.services.agent_registry.AgentRegistry", return_value=mock_registry):
        await sub.on_event(event)

    mock_registry.register.assert_called_once()


@pytest.mark.asyncio
async def test_session_subscriber__failure__does_not_raise():
    sub = SessionStateSubscriber()
    event = _make_event("agent_spawned")

    with patch("api.services.agent_registry.AgentRegistry", side_effect=RuntimeError("fail")):
        await sub.on_event(event)  # should not raise
