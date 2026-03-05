"""Pipeline runner — submits self-build problems to the OAK API,
monitors completion, reads judge verdicts, and triggers skill ingestion.
"""
from __future__ import annotations

__pattern__ = "TemplateMethod"

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import httpx

from oak_builder.problem_generator import GeneratedProblem

logger = logging.getLogger("oak.builder.pipeline_runner")

POLL_INTERVAL = 30
PROBLEM_TIMEOUT = 1200  # 20 minutes
WORKSPACE_BASE = "/workspaces"


@dataclass
class PipelineResult:
    problem_uuid: str
    domain_id: str
    scenario_id: str
    status: str
    judge_verdict: str | None = None
    judge_score: float | None = None
    skills_ingested: int = 0
    error: str | None = None


async def run_problem(
    problem: GeneratedProblem,
    *,
    api_url: str,
    pause_check: object | None = None,
) -> PipelineResult:
    """Submit a problem, start the pipeline, wait for completion, read verdict, ingest skills."""
    async with httpx.AsyncClient(base_url=api_url, timeout=60) as client:
        problem_uuid = await _submit_problem(client, problem)
        if not problem_uuid:
            return PipelineResult(
                problem_uuid=problem.problem_uuid,
                domain_id=problem.domain_id,
                scenario_id=problem.scenario_id,
                status="submit_failed",
                error="Failed to submit problem to API",
            )

        _copy_dataset_to_workspace(problem, problem_uuid)

        started = await _start_pipeline(client, problem_uuid)
        if not started:
            return PipelineResult(
                problem_uuid=problem_uuid,
                domain_id=problem.domain_id,
                scenario_id=problem.scenario_id,
                status="start_failed",
                error="Failed to start pipeline (harness container)",
            )

        status = await _poll_completion(
            client, problem_uuid, pause_check=pause_check,
        )

        verdict = None
        score = None
        if status == "complete":
            verdict, score = await _read_verdict(client, problem_uuid)

        skills_ingested = 0
        if status == "complete":
            skills_ingested = await _ingest_skills(client, problem_uuid)

        return PipelineResult(
            problem_uuid=problem_uuid,
            domain_id=problem.domain_id,
            scenario_id=problem.scenario_id,
            status=status,
            judge_verdict=verdict,
            judge_score=score,
            skills_ingested=skills_ingested,
        )


def _copy_dataset_to_workspace(
    problem: GeneratedProblem, problem_uuid: str,
) -> None:
    """Copy generated dataset and scripts into the problem workspace so harness containers can access them."""
    problem_ws = Path(WORKSPACE_BASE) / f"problem-{problem_uuid}"
    problem_ws.mkdir(parents=True, exist_ok=True)

    src_dir = Path(problem.csv_path).parent
    for src_file in src_dir.iterdir():
        if src_file.is_file():
            dst = problem_ws / src_file.name
            shutil.copy2(src_file, dst)
            logger.info("Copied %s → %s", src_file.name, dst)


async def _start_pipeline(
    client: httpx.AsyncClient, problem_uuid: str,
) -> bool:
    """Call POST /api/problems/{id}/start to launch the harness container."""
    try:
        resp = await client.post(f"/api/problems/{problem_uuid}/start")
        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                "Pipeline started for %s: container=%s",
                problem_uuid[:8],
                data.get("container_name", "?"),
            )
            return True
        logger.error(
            "Start failed (%d): %s", resp.status_code, resp.text[:300],
        )
        return False
    except httpx.HTTPError as exc:
        logger.error("Start HTTP error: %s", exc)
        return False


async def _submit_problem(
    client: httpx.AsyncClient, problem: GeneratedProblem,
) -> str | None:
    """POST the problem to the API, returning the UUID on success."""
    payload = {
        "title": problem.title,
        "description": problem.description,
        "source": "self-build",
        "data_paths": [problem.csv_path],
    }
    try:
        resp = await client.post("/api/problems", json=payload)
        if resp.status_code in (200, 201):
            data = resp.json()
            uuid = data.get("id") or data.get("uuid") or data.get("problem_id")
            logger.info("Problem submitted: %s", uuid)
            return uuid
        logger.error("Submit failed (%d): %s", resp.status_code, resp.text[:300])
        return None
    except httpx.HTTPError as exc:
        logger.error("Submit HTTP error: %s", exc)
        return None


async def _poll_completion(
    client: httpx.AsyncClient,
    problem_uuid: str,
    *,
    pause_check: object | None = None,
) -> str:
    """Poll until the problem is completed, failed, or times out."""
    elapsed = 0
    while elapsed < PROBLEM_TIMEOUT:
        if pause_check and hasattr(pause_check, "is_paused"):
            while pause_check.is_paused:
                logger.info("Sprint paused by resource guard, waiting...")
                await asyncio.sleep(10)

        try:
            resp = await client.get(f"/api/problems/{problem_uuid}")
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "unknown")
                if status in ("complete", "failed"):
                    logger.info(
                        "Problem %s finished: %s", problem_uuid[:8], status,
                    )
                    return status
        except httpx.HTTPError:
            pass

        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    logger.warning("Problem %s timed out after %ds", problem_uuid[:8], PROBLEM_TIMEOUT)
    return "timeout"


async def _read_verdict(
    client: httpx.AsyncClient, problem_uuid: str,
) -> tuple[str | None, float | None]:
    """Fetch judge verdict for a completed problem."""
    try:
        resp = await client.get(f"/api/judge_verdicts/{problem_uuid}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                latest = data[-1]
                return latest.get("verdict"), latest.get("score")
            if isinstance(data, dict):
                return data.get("verdict"), data.get("score")
    except httpx.HTTPError:
        logger.warning("Could not fetch verdict for %s", problem_uuid[:8])
    return None, None


async def _ingest_skills(
    client: httpx.AsyncClient, problem_uuid: str,
) -> int:
    """Trigger skill ingestion from the problem workspace."""
    try:
        resp = await client.post(f"/api/skills/ingest-workspace/{problem_uuid}")
        if resp.status_code == 200:
            data = resp.json()
            count = data.get("ingested", 0)
            if count > 0:
                logger.info(
                    "Ingested %d skill(s) from problem %s",
                    count, problem_uuid[:8],
                )
            return count
    except httpx.HTTPError:
        logger.warning("Skill ingestion failed for %s", problem_uuid[:8])
    return 0
