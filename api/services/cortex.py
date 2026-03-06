__pattern__ = "Strategy"

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import asyncpg
import httpx

from api.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModuleOutput:
    module: str
    salience: float
    action_type: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class CortexModule:
    """Base class for CORTEX+ specialist modules."""

    name: str = "base"

    async def compute(self, _state: dict[str, Any]) -> ModuleOutput:
        raise NotImplementedError


class PerceptionModule(CortexModule):
    """Monitors health metrics, telemetry, container status."""

    name = "perception"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        anomalies = []
        health = state.get("health", {})
        if not health.get("database", True):
            anomalies.append("database_unhealthy")
        if not health.get("redis", True):
            anomalies.append("redis_unhealthy")

        failed_recent = state.get("recent_failures", 0)
        # Cap at 0.7 so other modules can compete when failure count is high.
        # Previously min(1.0, ...) saturated at 1.0 with ≥7 failures, causing
        # a permanent perception monopoly (GWT never rotated to other modules).
        salience = min(0.7, failed_recent * 0.08 + len(anomalies) * 0.4)
        return ModuleOutput(
            module=self.name,
            salience=salience,
            action_type="diagnose" if anomalies else "monitor",
            payload={"anomalies": anomalies, "recent_failures": failed_recent},
        )


class MemoryModule(CortexModule):
    """Queries kernel grove, episodic memory, research cache."""

    name = "memory"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        kernel_count = state.get("kernel_count", 0)
        episode_count = state.get("episode_count", 0)
        salience = 0.3 if kernel_count > 0 else 0.1
        return ModuleOutput(
            module=self.name,
            salience=salience,
            action_type="enrich_context",
            payload={"kernels": kernel_count, "episodes": episode_count},
        )


class PlanningModule(CortexModule):
    """Uses manifest deltas and system goals to generate objectives."""

    name = "planning"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        deltas = state.get("manifest_deltas", [])
        active_problems = state.get("active_problems", 0)
        max_concurrent = state.get("max_concurrent", 3)

        if active_problems >= max_concurrent:
            return ModuleOutput(
                module=self.name, salience=0.0,
                action_type="wait", payload={"reason": "at_capacity"},
            )

        if not deltas:
            return ModuleOutput(
                module=self.name, salience=0.1,
                action_type="idle", payload={"reason": "no_deltas"},
            )

        top_delta = deltas[0]
        # Scale salience strongly with gap count so planning wins when work exists.
        # 5 gaps → 0.85, 7 gaps → 0.99, 8+ → 1.0
        salience = min(1.0, 0.5 + len(deltas) * 0.07)
        # Pass all deltas so execute_action can spawn multi-domain problems.
        available_slots = max_concurrent - active_problems
        return ModuleOutput(
            module=self.name, salience=salience,
            action_type="generate_objective",
            payload={
                "delta": top_delta,
                "total_gaps": len(deltas),
                "all_deltas": deltas,
                "available_slots": available_slots,
            },
        )


class MetacognitionModule(CortexModule):
    """Reads reward role scores and judge pass rate trends."""

    name = "metacognition"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        pass_rate = state.get("judge_pass_rate", 0.5)
        low_roles = state.get("low_scoring_roles", [])

        if pass_rate < 0.5 or low_roles:
            salience = 0.6 + (0.5 - pass_rate)
            return ModuleOutput(
                module=self.name, salience=min(1.0, salience),
                action_type="propose_amendment",
                payload={"pass_rate": pass_rate, "low_roles": low_roles},
            )
        return ModuleOutput(
            module=self.name, salience=0.1,
            action_type="monitor", payload={"pass_rate": pass_rate},
        )


class CuriosityModule(CortexModule):
    """Identifies unexplored domains from manifest."""

    name = "curiosity"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        uncovered = state.get("uncovered_domains", [])
        if not uncovered:
            return ModuleOutput(
                module=self.name, salience=0.05,
                action_type="idle", payload={},
            )

        salience = min(0.8, 0.3 + len(uncovered) * 0.05)
        return ModuleOutput(
            module=self.name, salience=salience,
            action_type="explore_domain",
            payload={"domain": uncovered[0], "total_uncovered": len(uncovered)},
        )


class SocialModule(CortexModule):
    """Prioritises operator submissions and human requests."""

    name = "social"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        pending_user = state.get("pending_user_problems", 0)
        if pending_user > 0:
            return ModuleOutput(
                module=self.name, salience=0.95,
                action_type="prioritise_user",
                payload={"pending": pending_user},
            )
        return ModuleOutput(
            module=self.name, salience=0.0,
            action_type="idle", payload={},
        )


class CriticModule(CortexModule):
    """Identifies regressions from recent problem outcomes."""

    name = "critic"

    async def compute(self, state: dict[str, Any]) -> ModuleOutput:
        recent_fail_rate = state.get("recent_fail_rate", 0.0)
        penalty_count = state.get("recent_penalties", 0)

        if recent_fail_rate > 0.4 or penalty_count > 5:
            # Cap penalty contribution so historical accumulation doesn't freeze planning.
            # penalty_count at 0.001 allows up to +0.1 at 100 events — a signal, not a dominator.
            salience = min(0.92, recent_fail_rate + penalty_count * 0.001)
            return ModuleOutput(
                module=self.name, salience=salience,
                action_type="identify_regression",
                payload={"fail_rate": recent_fail_rate, "penalties": penalty_count},
            )
        return ModuleOutput(
            module=self.name, salience=0.1,
            action_type="monitor", payload={},
        )


class CortexPlus:
    """
    CORTEX+ Cognitive Kernel implementing Global Workspace Theory.

    Each tick, all 7 modules compute salience scores. The highest-salience
    module wins broadcast and its action drives the system's next step.
    """

    def __init__(self) -> None:
        self.modules: list[CortexModule] = [
            PerceptionModule(),
            MemoryModule(),
            PlanningModule(),
            MetacognitionModule(),
            CuriosityModule(),
            SocialModule(),
            CriticModule(),
        ]
        self.broadcast_log: list[dict[str, Any]] = []
        self.running = False
        self.tick_interval = int(
            getattr(settings, "cortex_tick_interval", 120)
        )
        self.current_broadcast: ModuleOutput | None = None
        self._task: asyncio.Task[None] | None = None

    async def _gather_db_state(self, state: dict[str, Any]) -> None:
        """Populate state from database."""
        conn = await asyncpg.connect(settings.database_url)
        try:
            state["kernel_count"] = (
                await conn.fetchval(
                    "SELECT COUNT(*) FROM kernels WHERE status = 'permanent'"
                ) or 0
            )
            state["episode_count"] = (
                await conn.fetchval("SELECT COUNT(*) FROM episodes") or 0
            )
            state["active_problems"] = (
                await conn.fetchval(
                    """SELECT COUNT(*) FROM problems
                       WHERE status IN ('assembling', 'active')"""
                ) or 0
            )
            state["pending_user_problems"] = (
                await conn.fetchval(
                    "SELECT COUNT(*) FROM problems WHERE status = 'pending' AND source = 'user'"
                ) or 0
            )
            total_judged = await conn.fetchval("SELECT COUNT(*) FROM judge_verdicts")
            passed = await conn.fetchval(
                "SELECT COUNT(*) FROM judge_verdicts WHERE verdict = 'pass'"
            )
            if total_judged and total_judged > 0:
                state["judge_pass_rate"] = (passed or 0) / total_judged
            recent_failed = await conn.fetchval(
                """SELECT COUNT(*) FROM problems WHERE status = 'failed'
                   AND updated_at > NOW() - INTERVAL '7 days'"""
            )
            recent_total = await conn.fetchval(
                """SELECT COUNT(*) FROM problems
                   WHERE updated_at > NOW() - INTERVAL '7 days'"""
            )
            state["recent_failures"] = recent_failed or 0
            if recent_total and recent_total > 0:
                state["recent_fail_rate"] = (recent_failed or 0) / recent_total
            state["recent_penalties"] = (
                await conn.fetchval(
                    """SELECT COUNT(*) FROM reward_events
                       WHERE points < 0 AND created_at > NOW() - INTERVAL '7 days'"""
                ) or 0
            )
            low_roles_rows = await conn.fetch(
                """SELECT role FROM role_scores
                   WHERE rolling_30d_points < 0
                   ORDER BY rolling_30d_points ASC LIMIT 5"""
            )
            state["low_scoring_roles"] = [r["role"] for r in low_roles_rows]
        finally:
            await conn.close()

    async def _gather_manifest_state(self, state: dict[str, Any]) -> None:
        """Populate manifest deltas and uncovered domains."""
        manifest_path = Path(settings.acorn_root) / "manifest_domains.json"
        if not manifest_path.exists():
            return
        with manifest_path.open() as f:
            manifest = json.load(f)
        domains = manifest.get("domains", {})
        try:
            conn = await asyncpg.connect(settings.database_url)
            try:
                rows = await conn.fetch(
                    """SELECT category, COUNT(*) as cnt
                       FROM kernels WHERE status IN ('permanent', 'probationary') GROUP BY category"""
                )
                cat_counts = {r["category"]: r["cnt"] for r in rows}
            finally:
                await conn.close()
        except Exception:
            cat_counts = {}
        deltas = []
        uncovered = []
        for domain, spec in domains.items():
            have = cat_counts.get(domain, 0)
            want = spec.get("target_kernels", 3)
            if have < want:
                delta: dict[str, Any] = {
                    "type": "missing_kernels",
                    "domain": domain,
                    "have": have,
                    "need": want,
                    "gap": want - have,
                }
                if "core_concepts" in spec:
                    delta["core_concepts"] = spec["core_concepts"]
                deltas.append(delta)
            if have == 0:
                uncovered.append(domain)
        state["manifest_deltas"] = sorted(deltas, key=lambda d: d["gap"], reverse=True)
        state["uncovered_domains"] = uncovered

    async def gather_state(self) -> dict[str, Any]:
        """Collect system state for module computation."""
        state: dict[str, Any] = {
            "health": {"database": True, "redis": True},
            "kernel_count": 0,
            "episode_count": 0,
            "manifest_deltas": [],
            "active_problems": 0,
            "max_concurrent": settings.max_concurrent_problems,
            "judge_pass_rate": 0.5,
            "low_scoring_roles": [],
            "uncovered_domains": [],
            "pending_user_problems": 0,
            "recent_failures": 0,
            "recent_fail_rate": 0.0,
            "recent_penalties": 0,
        }
        try:
            await self._gather_db_state(state)
        except Exception:
            logger.warning("CORTEX+ state gathering partially failed", exc_info=True)
        try:
            await self._gather_manifest_state(state)
        except Exception:
            logger.warning("CORTEX+ manifest loading failed", exc_info=True)
        return state

    async def tick(self) -> ModuleOutput | None:
        """Run one cognitive tick: all modules compute, highest salience wins."""
        state = await self.gather_state()
        outputs = []
        for mod in self.modules:
            try:
                out = await mod.compute(state)
                outputs.append(out)
            except Exception:
                logger.warning("Module %s failed", mod.name, exc_info=True)

        if not outputs:
            return None

        # Habituation decay: dampen the consecutive winner so other modules get
        # airtime. Each win multiplies the winner's effective salience by 0.85,
        # resetting when a different module takes over.
        last_winner = self.current_broadcast.module if self.current_broadcast else None
        consecutive = getattr(self, "_consecutive_wins", 0)
        import random as _random
        adjusted = []
        for o in outputs:
            decay = (0.85 ** consecutive) if o.module == last_winner else 1.0
            adjusted.append((o.salience * decay, _random.random(), o))
        adjusted.sort(key=lambda t: (t[0], t[1]), reverse=True)
        winner = adjusted[0][2]
        self._consecutive_wins = (consecutive + 1) if winner.module == last_winner else 1
        self.current_broadcast = winner
        entry = {
            "module": winner.module,
            "salience": winner.salience,
            "action_type": winner.action_type,
            "payload": winner.payload,
            "timestamp": winner.timestamp,
            "all_saliences": {o.module: o.salience for o in outputs},
        }
        self.broadcast_log.append(entry)
        if len(self.broadcast_log) > 500:
            self.broadcast_log = self.broadcast_log[-250:]

        logger.info(
            "CORTEX+ broadcast: %s (salience=%.2f, action=%s)",
            winner.module, winner.salience, winner.action_type,
        )

        await self.execute_action(winner, state)
        return winner

    async def execute_action(
        self, winner: ModuleOutput, _state: dict[str, Any],
    ) -> None:
        """Execute the winning module's action."""
        try:
            if winner.action_type == "generate_objective":
                await self._submit_self_improvement(winner.payload)
            elif winner.action_type == "explore_domain":
                await self._submit_exploration(winner.payload)
            elif winner.action_type == "prioritise_user":
                logger.info("CORTEX+ Social: user problems take priority")
            elif winner.action_type == "propose_amendment":
                pass_rate = winner.payload.get("pass_rate", 0)
                low_roles = winner.payload.get("low_roles", [])
                logger.info(
                    "CORTEX+ Metacognition: pass_rate=%.2f low_roles=%s — applying remediation",
                    pass_rate, low_roles,
                )
                # Always attempt kernel auto-promotion
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        await client.post(
                            f"http://localhost:{settings.port}/api/kernels/auto-promote",
                            json={"min_uses": 1},
                        )
                except Exception:
                    pass
                # If pass rate critically low, submit a meta-improvement problem
                if pass_rate < 0.35 and "orchestrator" in low_roles:
                    try:
                        async with httpx.AsyncClient(timeout=15) as client:
                            await client.post(
                                f"http://localhost:{settings.port}/api/problems",
                                json={
                                    "title": "CORTEX+ meta: analyze recent failures and identify root causes",
                                    "description": (
                                        f"The system pass rate is {pass_rate:.1%}. "
                                        "Analyze the last 10 failed problem workspaces in /home/sharaths/acorn-workspaces/. "
                                        "For each failure: read SOLUTION.md, judge_verdict.json, and PROBLEM.md. "
                                        "Identify the top 3 root causes of failure (e.g. 'no .py files', 'wrong dataset', 'generic output'). "
                                        "Write a SOLUTION.md with: ## Root Causes, ## Recommendations (specific prompt improvements), "
                                        "## Success Patterns (what the passing problems did differently). "
                                        "This analysis will guide CORTEX+ to improve future problem framing."
                                    ),
                                    "source": "cortex",
                                },
                            )
                            logger.info("CORTEX+ Metacognition: submitted meta-analysis problem")
                    except Exception:
                        pass
            elif winner.action_type == "identify_regression":
                fail_rate = winner.payload.get("fail_rate", 0)
                logger.info("CORTEX+ Critic: regression fail_rate=%.2f, cooling domain", fail_rate)
                if fail_rate > 0.7:
                    try:
                        async with httpx.AsyncClient(timeout=15) as client:
                            await client.post(
                                f"http://localhost:{settings.port}/api/problems",
                                json={
                                    "title": "CORTEX+ recovery: simple data exploration",
                                    "description": "Generate a synthetic dataset of 200 rows with columns: id, value, category, timestamp. Compute summary statistics (mean, std, min, max per category). Write findings to SOLUTION.md.",
                                    "source": "cortex",
                                },
                            )
                    except Exception:
                        pass
                # Also ensure reasoning model is available for judge role
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        await client.post(
                            f"http://localhost:{settings.port}/api/models/pull",
                            json={"name": settings.reasoning_model},
                        )
                except Exception:
                    pass
            elif winner.action_type in ("diagnose", "monitor", "idle", "wait"):
                pass
        except Exception:
            logger.warning(
                "CORTEX+ action execution failed: %s", winner.action_type,
                exc_info=True,
            )

    async def _submit_self_improvement(self, payload: dict[str, Any]) -> None:
        """Submit self-improvement problems for multiple gap domains in parallel."""
        all_deltas = payload.get("all_deltas", [payload.get("delta", {})])
        available_slots = payload.get("available_slots", 1)
        # Spawn problems for top N domains where N = available capacity (max 3)
        domains_to_fill = all_deltas[: min(3, max(1, available_slots))]

        async with httpx.AsyncClient(timeout=30) as client:
            for delta in domains_to_fill:
                domain = delta.get("domain", "general")
                gap = delta.get("gap", 1)
                concepts = delta.get("core_concepts", [domain])
                problem_desc = (
                    f"Build {gap} reusable kernel(s) for the '{domain}' domain. "
                    f"Key concepts to cover: {', '.join(concepts[:4])}. "
                    f"For each concept: write a parameterized Python function to /workspace/{{concept}}.py, "
                    f"test it with sample data, and write /workspace/SOLUTION.md listing each kernel's "
                    f"inputs, outputs, and a concrete usage example with actual output values."
                )
                try:
                    await client.post(
                        f"http://localhost:{settings.port}/api/problems",
                        json={
                            "title": f"CORTEX+ objective: {domain} kernels",
                            "description": problem_desc,
                            "source": "cortex",
                        },
                    )
                    logger.info("CORTEX+ planning: submitted kernel problem for domain '%s'", domain)
                except Exception:
                    logger.warning("Failed to submit self-improvement problem for domain %s", domain)

    async def _submit_exploration(self, payload: dict[str, Any]) -> None:
        """Submit an exploration problem for an uncovered domain."""
        domain = payload.get("domain", "unknown")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(
                    f"http://localhost:{settings.port}/api/problems",
                    json={
                        "title": f"CORTEX+ exploration: {domain}",
                        "description": (
                            f"Explore the '{domain}' domain. Research key concepts, "
                            f"build initial analytical patterns, and create at least one "
                            f"kernel for future reuse."
                        ),
                        "source": "cortex",
                    },
                )
        except Exception:
            logger.warning("Failed to submit exploration problem", exc_info=True)

    async def run(self) -> None:
        """Main cognitive loop."""
        self.running = True
        logger.info("CORTEX+ cognitive kernel starting (tick=%ds)", self.tick_interval)
        while self.running:
            try:
                await self.tick()
            except Exception:
                logger.error("CORTEX+ tick failed", exc_info=True)
            await asyncio.sleep(self.tick_interval)

    def stop(self) -> None:
        self.running = False

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "current_broadcast": {
                "module": self.current_broadcast.module,
                "salience": self.current_broadcast.salience,
                "action_type": self.current_broadcast.action_type,
                "payload": self.current_broadcast.payload,
            } if self.current_broadcast else None,
            "tick_interval": self.tick_interval,
            "broadcast_log_size": len(self.broadcast_log),
        }

    def get_broadcast_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.broadcast_log[-limit:]


_cortex: CortexPlus | None = None


def get_cortex() -> CortexPlus:
    global _cortex
    if _cortex is None:
        _cortex = CortexPlus()
    return _cortex
