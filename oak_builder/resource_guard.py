"""Resource guard — pauses self-build sprints when user problems arrive.

Primary signal: Redis pub/sub on ``oak:events`` channel.
Fallback: HTTP poll of ``GET /api/problems`` every 15 seconds.
"""
from __future__ import annotations

__pattern__ = "Observer"

import asyncio
import logging
import subprocess

import httpx

logger = logging.getLogger("oak.builder.resource_guard")

POLL_INTERVAL = 15
USER_PROBLEM_TIMEOUT = 1800  # 30 min before graceful termination


class ResourceGuard:
    """Monitors for active user problems and pauses/resumes builder containers."""

    def __init__(self, *, api_url: str, redis_url: str) -> None:
        self.api_url = api_url
        self.redis_url = redis_url
        self.is_paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused initially
        self._watch_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._watch_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

    async def wait_if_paused(self) -> None:
        """Block until the guard is not paused."""
        await self._pause_event.wait()

    async def _poll_loop(self) -> None:
        """Fallback polling loop — checks for user problems periodically."""
        while True:
            try:
                user_active = await self._check_user_problems()
                if user_active and not self.is_paused:
                    await self._pause()
                elif not user_active and self.is_paused:
                    await self._resume()
            except Exception as exc:
                logger.debug("Guard poll error: %s", exc)
            await asyncio.sleep(POLL_INTERVAL)

    async def _check_user_problems(self) -> bool:
        """Query API for active non-self-build problems."""
        try:
            async with httpx.AsyncClient(
                base_url=self.api_url, timeout=10,
            ) as client:
                resp = await client.get("/api/problems")
                if resp.status_code != 200:
                    return False
                problems = resp.json()
                if not isinstance(problems, list):
                    return False
                return any(
                    p.get("status") in ("active", "assembling")
                    and p.get("source", "user") != "self-build"
                    and not (p.get("title") or "").startswith("[self-build]")
                    for p in problems
                )
        except httpx.HTTPError:
            return False

    async def _pause(self) -> None:
        """Pause all self-build harness containers."""
        logger.warning("User problem detected — pausing self-build containers")
        self.is_paused = True
        self._pause_event.clear()
        _pause_self_build_containers()

    async def _resume(self) -> None:
        """Resume paused self-build containers."""
        logger.info("User problems cleared — resuming self-build containers")
        self.is_paused = False
        self._pause_event.set()
        _unpause_self_build_containers()


def _pause_self_build_containers() -> None:
    """docker pause all containers whose name starts with oak-*-self-build."""
    _docker_action("pause")


def _unpause_self_build_containers() -> None:
    """docker unpause all paused self-build containers."""
    _docker_action("unpause")


def _docker_action(action: str) -> None:
    """Execute docker pause/unpause on self-build harness containers."""
    try:
        result = subprocess.run(
            [
                "docker", "ps", "-q",
                "--filter", "name=oak-",
                "--filter", "label=oak.source=self-build",
            ],
            capture_output=True, text=True, timeout=10,
        )
        containers = result.stdout.strip().split("\n")
        containers = [c for c in containers if c]
        for cid in containers:
            subprocess.run(
                ["docker", action, cid],
                capture_output=True, timeout=10,
            )
            logger.debug("docker %s %s", action, cid[:12])
    except Exception as exc:
        logger.warning("docker %s failed: %s", action, exc)
