__pattern__ = "Repository"

from functools import lru_cache
from api.config import OAKSettings
from api.events.bus import EventBus, TelemetrySubscriber, WebSocketSubscriber, EpisodicMemorySubscriber


@lru_cache
def get_settings() -> OAKSettings:
    return OAKSettings()


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        _event_bus.subscribe(TelemetrySubscriber())
        _event_bus.subscribe(EpisodicMemorySubscriber())
        _event_bus.subscribe(WebSocketSubscriber())
    return _event_bus
