"""Unit tests for api.events.bus EventBus and subscriber dispatch."""
import time

import pytest

from api.events.bus import AgentEvent, EventBus, EventSubscriber, TelemetrySubscriber


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
