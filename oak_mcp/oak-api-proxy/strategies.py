# oak_mcp/oak-api-proxy/strategies.py
__pattern__ = "Strategy"

from abc import ABC, abstractmethod

class RoutingStrategy(ABC):
    """Decides, given a request and a local response, which backend to use."""

    @abstractmethod
    async def should_escalate(self, request_body: dict, local_response: dict) -> bool:
        """Return True to escalate to Claude API; False to use local response."""
        ...

class PassthroughStrategy(RoutingStrategy):
    """Always returns False. Default in v1 — no escalation, fully local."""
    async def should_escalate(self, request_body, local_response) -> bool:
        return False

class StallDetectionStrategy(RoutingStrategy):
    """Escalates on empty, too-short, or phrase-triggered responses.
    Enabled only when STALL_DETECTION_ENABLED=true."""
    def __init__(self, min_tokens: int, stall_phrases: list[str]):
        self.min_tokens = min_tokens
        self.stall_phrases = stall_phrases

    async def should_escalate(self, request_body, local_response) -> bool:
        text = local_response.get("content", [{}])[0].get("text", "").lower().strip()
        if not text:
            return True
        if len(text.split()) < self.min_tokens:
            return True
        return any(text.startswith(p) for p in self.stall_phrases)

class ConfidenceThresholdStrategy(RoutingStrategy):
    """Escalates when the model's self-reported confidence field drops below threshold.
    Used in mini profile where local model capability is more limited."""
    def __init__(self, threshold: float):
        self.threshold = threshold

    async def should_escalate(self, request_body, local_response) -> bool:
        confidence = local_response.get("confidence", 1.0)
        return confidence < self.threshold
