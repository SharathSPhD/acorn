"""OAK Builder — the self-build sprint loop.

This is the entry point for the oak-builder Docker service.  It runs
an asyncio loop that executes sprints (scan → synthesize → run →
review → propose → commit), respects wall-clock limits, and halts
via the circuit breaker when the pipeline is fundamentally broken.
"""
from __future__ import annotations

__pattern__ = "TemplateMethod"

import asyncio
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from oak_builder.circuit_breaker import CircuitBreaker
from oak_builder.gap_analyzer import analyze_gaps
from oak_builder.pipeline_runner import PipelineResult, run_problem
from oak_builder.problem_generator import generate_problem
from oak_builder.resource_guard import ResourceGuard
from oak_builder.self_commit import propose_and_commit
from oak_builder.sprint_log import SprintLog, SprintResult

logging.basicConfig(
    level=logging.INFO,
    format="[oak-builder %(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("oak.builder.main")

API_URL = os.environ.get("OAK_API_URL", "http://oak-api:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://oak-redis:6379")
REPO_PATH = os.environ.get("OAK_REPO_PATH", "/oak-repo")
WORKSPACE_BASE = os.environ.get("OAK_WORKSPACE_BASE", "/workspaces")
OLLAMA_URL = os.environ.get("OAK_BUILDER_OLLAMA_URL", "http://oak-api-proxy:9000")

SPRINT_INTERVAL = int(os.environ.get("OAK_BUILDER_SPRINT_INTERVAL", "3600"))
REST_SECONDS = int(os.environ.get("OAK_BUILDER_REST_SECONDS", "900"))
MAX_SPRINTS = int(os.environ.get("OAK_BUILDER_MAX_SPRINTS", "8"))
WALL_LIMIT = int(os.environ.get("OAK_BUILDER_WALL_LIMIT", "28800"))
CB_THRESHOLD = int(os.environ.get("OAK_BUILDER_CB_THRESHOLD", "4"))
WORKTREE_PATH = os.environ.get("OAK_BUILDER_WORKTREE_PATH", "/oak-builder-wt")
CODER_MODEL = os.environ.get("OAK_BUILDER_CODER_MODEL", "qwen3-coder")
REASONING_MODEL = os.environ.get("OAK_BUILDER_REASONING_MODEL", "llama3.3:70b")
RELEASE_THRESHOLD = int(os.environ.get("OAK_BUILDER_RELEASE_THRESHOLD", "5"))

MANIFEST_DOMAINS_PATH = Path(REPO_PATH) / "manifest_domains.json"
SPRINT_LOG_PATH = os.path.join(WORKSPACE_BASE, "builder", "sprint_log.json")

_state: dict = {
    "status": "idle",
    "current_sprint": None,
    "last_sprint_result": None,
}


def get_state() -> dict:
    return dict(_state)


async def run_sprint(
    sprint_number: int,
    *,
    breaker: CircuitBreaker,
    guard: ResourceGuard,
    sprint_log: SprintLog,
) -> SprintResult:
    """Execute one complete self-build sprint."""
    _state["status"] = "scanning"
    _state["current_sprint"] = sprint_number
    started = datetime.now(UTC).isoformat()

    result = SprintResult(
        sprint_number=sprint_number,
        started_at=started,
        finished_at="",
    )

    # ── SCAN ──────────────────────────────────────────────────────────
    logger.info("Sprint %d: SCAN — analyzing gaps", sprint_number)
    gaps = await analyze_gaps(
        API_URL,
        sprint_number=sprint_number,
        top_n=3,
        manifest_path=MANIFEST_DOMAINS_PATH,
    )

    if not gaps:
        logger.info("No gaps identified — sprint complete (no work)")
        result.finished_at = datetime.now(UTC).isoformat()
        return result

    # ── SYNTHESIZE + RUN ──────────────────────────────────────────────
    _state["status"] = "synthesizing"
    manifest_companies = _load_companies()

    pipeline_results: list[PipelineResult] = []
    for gap in gaps:
        await guard.wait_if_paused()

        _state["status"] = "synthesizing"
        logger.info(
            "Sprint %d: SYNTHESIZE — %s / %s",
            sprint_number, gap.domain_name, gap.scenario.get("id"),
        )

        problem = await generate_problem(
            gap,
            workspace_base=WORKSPACE_BASE,
            ollama_url=OLLAMA_URL,
            model=CODER_MODEL,
            manifest_companies=manifest_companies,
        )
        if not problem:
            result.problems_failed += 1
            continue

        _state["status"] = "running"
        result.problems_submitted += 1
        logger.info(
            "Sprint %d: RUN — submitting %s", sprint_number, problem.title,
        )

        pr = await run_problem(
            problem, api_url=API_URL, pause_check=guard,
        )
        pipeline_results.append(pr)

        if pr.status == "complete" and pr.judge_verdict == "pass":
            result.problems_passed += 1
            result.skills_ingested += pr.skills_ingested
            result.domain_results[pr.domain_id] = {
                "scenario_id": pr.scenario_id,
                "judge_score": pr.judge_score,
                "skills_ingested": pr.skills_ingested,
            }
        else:
            result.problems_failed += 1
            result.domain_results[pr.domain_id] = {
                "scenario_id": pr.scenario_id,
                "status": pr.status,
                "error": pr.error,
            }

    # ── REVIEW + PROPOSE ──────────────────────────────────────────────
    _state["status"] = "reviewing"
    successful_count = result.problems_passed

    if successful_count > 0:
        logger.info(
            "Sprint %d: PROPOSE — %d/%d problems passed",
            sprint_number, successful_count, result.problems_submitted,
        )

        proposals = await _get_meta_proposals()
        if proposals and proposals.get("file_changes"):
            _state["status"] = "committing"
            commit_result = await propose_and_commit(
                repo_path=REPO_PATH,
                worktree_path=WORKTREE_PATH,
                domain_id=gaps[0].domain_id,
                proposals=proposals,
                ollama_url=OLLAMA_URL,
                reasoning_model=REASONING_MODEL,
            )
            result.changes_committed = commit_result.merged
            result.commit_branch = commit_result.branch
    else:
        logger.info(
            "Sprint %d: No successful problems — skipping proposals",
            sprint_number,
        )

    # ── LOG ───────────────────────────────────────────────────────────
    result.finished_at = datetime.now(UTC).isoformat()
    result.circuit_breaker_state = breaker.state

    breaker.record_sprint(successful_verdicts=successful_count)
    result.circuit_breaker_state = breaker.state

    sprint_log.record_sprint(result)
    _state["last_sprint_result"] = {
        "sprint": sprint_number,
        "passed": result.problems_passed,
        "failed": result.problems_failed,
        "skills": result.skills_ingested,
        "committed": result.changes_committed,
        "breaker": breaker.state,
    }

    # ── RELEASE ───────────────────────────────────────────────────────
    if sprint_log.should_release():
        tag = sprint_log.create_release(REPO_PATH)
        if tag:
            logger.info("Sprint %d: RELEASE — tagged %s", sprint_number, tag)

    _state["status"] = "resting"
    return result


async def _get_meta_proposals() -> dict:
    """Fetch proposals from the meta-agent via the API."""
    try:
        async with httpx.AsyncClient(
            base_url=API_URL, timeout=30,
        ) as client:
            resp = await client.get("/api/meta/proposals")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("proposals"):
                    return data
                if isinstance(data, list) and data:
                    return {"file_changes": [], "proposals": data}
    except httpx.HTTPError as exc:
        logger.warning("Could not fetch meta proposals: %s", exc)
    return {}


def _load_companies() -> dict:
    """Load canonical companies from manifest_domains.json."""
    try:
        manifest = json.loads(MANIFEST_DOMAINS_PATH.read_text())
        return manifest.get("canonical_companies", {})
    except Exception:
        return {}


async def main() -> None:
    """Main entry point: run sprints until wall-clock limit or max sprints."""
    logger.info(
        "OAK Builder starting (sprints=%d, rest=%ds, wall=%ds, cb=%d)",
        MAX_SPRINTS, REST_SECONDS, WALL_LIMIT, CB_THRESHOLD,
    )

    await _wait_for_api()

    breaker = CircuitBreaker(threshold=CB_THRESHOLD)
    guard = ResourceGuard(api_url=API_URL, redis_url=REDIS_URL)
    sprint_log = SprintLog(
        log_path=SPRINT_LOG_PATH,
        release_threshold=RELEASE_THRESHOLD,
    )

    await guard.start()
    session_start = time.monotonic()
    sprint_number = sprint_log.sprint_count

    try:
        for _i in range(MAX_SPRINTS):
            elapsed = time.monotonic() - session_start
            if elapsed >= WALL_LIMIT:
                logger.info("Wall-clock limit reached (%.0fs), stopping", elapsed)
                break

            if breaker.is_halted:
                logger.error("Circuit breaker HALTED — builder stopped")
                _state["status"] = "halted"
                break

            await guard.wait_if_paused()

            sprint_number += 1
            logger.info(
                "=== Sprint %d starting (session elapsed: %.0fs) ===",
                sprint_number, elapsed,
            )
            await run_sprint(
                sprint_number,
                breaker=breaker,
                guard=guard,
                sprint_log=sprint_log,
            )

            rest = REST_SECONDS * breaker.rest_multiplier()
            logger.info("Resting for %ds before next sprint...", rest)
            _state["status"] = "resting"
            await asyncio.sleep(rest)

    finally:
        await guard.stop()
        _state["status"] = "stopped"
        logger.info(
            "Builder session ended: %d sprints, %d total skills",
            sprint_number - sprint_log.sprint_count + (MAX_SPRINTS if not breaker.is_halted else 0),
            sprint_log.to_dict()["total_skills"],
        )


async def _wait_for_api() -> None:
    """Wait until oak-api is healthy before starting sprints."""
    logger.info("Waiting for oak-api at %s...", API_URL)
    for _attempt in range(60):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{API_URL}/health")
                if resp.status_code == 200:
                    logger.info("oak-api is healthy")
                    return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(5)
    logger.error("oak-api not available after 5 minutes, starting anyway")


if __name__ == "__main__":
    asyncio.run(main())
