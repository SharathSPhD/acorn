"""Unit tests for EventBus."""
import asyncio
import time
from api.events.bus import EventBus, AgentEvent, EventSubscriber


class _RecordingSubscriber(EventSubscriber):
    def __init__(self):
        self.received: list[AgentEvent] = []

    async def on_event(self, event: AgentEvent) -> None:
        self.received.append(event)


def _make_event(**kwargs) -> AgentEvent:
    defaults = dict(
        agent_id="a1",
        event_type="tool_called",
        problem_uuid="prob-uuid-001",
        payload={},
        timestamp_utc=time.time(),
    )
    defaults.update(kwargs)
    return AgentEvent(**defaults)


def test_event_bus__subscribe__subscriber_added():
    bus = EventBus()
    sub = _RecordingSubscriber()
    bus.subscribe(sub)
    assert sub in bus._subscribers


def test_event_bus__publish__all_subscribers_notified():
    bus = EventBus()
    sub1 = _RecordingSubscriber()
    sub2 = _RecordingSubscriber()
    bus.subscribe(sub1)
    bus.subscribe(sub2)
    event = _make_event()
    asyncio.get_event_loop().run_until_complete(bus.publish(event))
    assert len(sub1.received) == 1
    assert len(sub2.received) == 1
    assert sub1.received[0] is event


def test_event_bus__publish_no_subscribers__no_error():
    bus = EventBus()
    event = _make_event()
    asyncio.get_event_loop().run_until_complete(bus.publish(event))  # no raise
