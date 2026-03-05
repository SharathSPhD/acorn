"""Manifest Engine: perceives desired vs actual state and computes deltas."""
__pattern__ = "Strategy"

import json
import logging
from pathlib import Path
from typing import Any

import asyncpg
import httpx

from api.config import settings

logger = logging.getLogger(__name__)


class ManifestEngine:
    """Compares manifest desired state to actual system state and produces deltas."""

    def __init__(self, manifest_path: str) -> None:
        self._manifest_path = Path(manifest_path)
        self._manifest: dict[str, Any] | None = None

    def _load_manifest(self) -> dict[str, Any]:
        """Load and cache manifest_domains.json."""
        if self._manifest is None:
            raw = self._manifest_path.read_text()
            self._manifest = json.loads(raw)
        assert self._manifest is not None
        return self._manifest

    async def perceive(self) -> dict[str, Any]:
        """Read desired state from file and query actual state from DB, Ollama, and filesystem."""
        desired = self._load_manifest()

        # Actual: kernels per domain (category)
        kernels_by_domain: dict[str, int] = {}
        try:
            conn = await asyncpg.connect(settings.database_url)
            try:
                rows = await conn.fetch(
                    """
                    SELECT category, COUNT(*) AS cnt
                    FROM kernels
                    WHERE status = 'permanent'
                    GROUP BY category
                    """
                )
                kernels_by_domain = {r["category"]: r["cnt"] for r in rows}
            finally:
                await conn.close()
        except Exception as exc:
            logger.warning("Failed to query kernels: %s", exc)

        # Actual: available Ollama models
        available_models: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    available_models = [
                        m.get("name", "") for m in data.get("models", [])
                        if m.get("name")
                    ]
        except Exception as exc:
            logger.warning("Failed to fetch Ollama models: %s", exc)

        # Actual: agent definitions from .claude/agents/
        agents_path = Path(settings.acorn_root) / ".claude" / "agents"
        if not agents_path.exists():
            # Fallback for local dev: project root relative to this file
            agents_path = Path(__file__).resolve().parents[2] / ".claude" / "agents"
        present_agents: list[str] = []
        if agents_path.exists():
            present_agents = [
                f.stem for f in agents_path.iterdir()
                if f.is_file() and f.suffix.lower() == ".md"
            ]

        actual = {
            "kernels_by_domain": kernels_by_domain,
            "available_models": available_models,
            "present_agents": present_agents,
        }
        return {"desired": desired, "actual": actual}

    async def diff(self, desired: dict[str, Any], actual: dict[str, Any]) -> list[dict[str, Any]]:
        """Compute deltas between desired and actual state."""
        deltas: list[dict[str, Any]] = []

        # Missing kernels per domain
        domains = desired.get("domains", {})
        kernels_by_domain = actual.get("kernels_by_domain", {})
        for domain, spec in domains.items():
            target = spec.get("target_kernels", 3)
            current = kernels_by_domain.get(domain, 0)
            if current < target:
                deltas.append({
                    "type": "missing_kernels",
                    "domain": domain,
                    "target": target,
                    "actual": current,
                    "gap": target - current,
                })

        # Missing required agents
        agent_catalogue = desired.get("agent_catalogue", {})
        present_agents = set(actual.get("present_agents", []))
        for agent_id, agent_spec in agent_catalogue.items():
            if agent_spec.get("required") and agent_id not in present_agents:
                deltas.append({
                    "type": "missing_agent",
                    "agent_id": agent_id,
                })

        # Model routing mismatches (desired model not available)
        model_routing = desired.get("model_routing", {})
        available_models = set(actual.get("available_models", []))
        for agent_id, desired_model in model_routing.items():
            if desired_model and desired_model not in available_models:
                deltas.append({
                    "type": "model_mismatch",
                    "agent_id": agent_id,
                    "desired_model": desired_model,
                    "available": list(available_models)[:10],  # Sample
                })

        return deltas

    async def reconcile(self) -> list[dict[str, Any]]:
        """Orchestrate perceive -> diff and return deltas."""
        perceived = await self.perceive()
        desired = perceived["desired"]
        actual = perceived["actual"]
        return await self.diff(desired, actual)
