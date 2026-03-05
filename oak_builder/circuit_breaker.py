"""Circuit breaker for the self-build sprint loop.

Tracks consecutive sprint failures and halts the builder when the pipeline
is fundamentally broken, preventing wasted GPU cycles.
"""
from __future__ import annotations

__pattern__ = "Strategy"

import json
import logging
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger("oak.builder.circuit_breaker")


class BreakerState(StrEnum):
    CLOSED = "closed"       # Normal operation
    DEGRADED = "degraded"   # 2+ failures — doubled rest interval
    HALTED = "halted"       # 4+ failures — stopped, needs manual resume


@dataclass
class CircuitBreaker:
    threshold: int = 4
    consecutive_failures: int = 0
    state: BreakerState = BreakerState.CLOSED
    _history: list[dict] = field(default_factory=list)

    def record_sprint(self, *, successful_verdicts: int) -> None:
        entry = {
            "successful_verdicts": successful_verdicts,
            "state_before": self.state,
        }
        if successful_verdicts == 0:
            self.consecutive_failures += 1
            logger.warning(
                "Sprint produced zero verdicts (%d consecutive failures)",
                self.consecutive_failures,
            )
        else:
            self.consecutive_failures = 0
            self.state = BreakerState.CLOSED

        if self.consecutive_failures >= self.threshold:
            self.state = BreakerState.HALTED
            logger.error(
                "Circuit breaker HALTED after %d consecutive failures",
                self.consecutive_failures,
            )
        elif self.consecutive_failures >= 2:
            self.state = BreakerState.DEGRADED
            logger.warning(
                "Circuit breaker DEGRADED — rest interval will be doubled"
            )

        entry["state_after"] = self.state
        self._history.append(entry)

    def rest_multiplier(self) -> int:
        if self.state == BreakerState.DEGRADED:
            return 2
        return 1

    @property
    def is_halted(self) -> bool:
        return self.state == BreakerState.HALTED

    def reset(self) -> None:
        self.consecutive_failures = 0
        self.state = BreakerState.CLOSED
        logger.info("Circuit breaker reset to CLOSED")

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "consecutive_failures": self.consecutive_failures,
            "threshold": self.threshold,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
