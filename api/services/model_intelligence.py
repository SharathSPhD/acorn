"""Model intelligence service — benchmarks models and produces SWOT analysis."""
__pattern__ = "Strategy"

import json
import logging
import time
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings

logger = logging.getLogger(__name__)

_BENCHMARK_PROMPTS = [
    {
        "capability": "coding",
        "prompt": "Write a Python function to calculate fibonacci. Include a docstring.",
    },
    {
        "capability": "analysis",
        "prompt": "Given sales data [100, 120, 90, 150, 180], identify the trend.",
    },
    {
        "capability": "reasoning",
        "prompt": "If all A are B, and all B are C, are all A C? Explain briefly.",
    },
    {
        "capability": "instruction_following",
        "prompt": "Return ONLY the word 'hello' with no other text.",
    },
]

_TASK_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "ingest": {"coding": 0.8, "analysis": 0.1, "reasoning": 0.05, "instruction_following": 0.05},
    "analyse": {"coding": 0.2, "analysis": 0.7, "reasoning": 0.05, "instruction_following": 0.05},
    "model": {"coding": 0.4, "analysis": 0.1, "reasoning": 0.4, "instruction_following": 0.1},
    "synthesise": {
        "coding": 0.5, "analysis": 0.4, "reasoning": 0.05, "instruction_following": 0.05
    },
    "validate": {"coding": 0.1, "analysis": 0.1, "reasoning": 0.4, "instruction_following": 0.4},
}


class ModelIntelligenceService:
    """Evaluates models and produces SWOT analysis."""

    def __init__(
        self,
        ollama_url: str | None = None,
        relay_url: str | None = None,
    ) -> None:
        self.ollama_url = (ollama_url or settings.ollama_base_url).rstrip("/")
        self.relay_url = (relay_url or settings.anthropic_base_url).rstrip("/")

    async def list_available_models(self) -> list[dict[str, Any]]:
        """GET {ollama_url}/api/tags -> list of models."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                if resp.status_code != 200:
                    logger.warning("Ollama /api/tags returned %d", resp.status_code)
                    return []
                data = resp.json()
                return data.get("models", [])
        except Exception as e:
            logger.exception("Failed to list models: %s", e)
            return []

    async def benchmark_model(self, model_name: str) -> dict[str, Any]:
        """Run standard prompts against a model and measure quality + speed."""
        scores: dict[str, float] = {}
        latencies: list[float] = []
        total_tokens = 0

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.anthropic_auth_token}",
            "anthropic-version": "2023-06-01",
            "x-acorn-model": model_name,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            for item in _BENCHMARK_PROMPTS:
                cap, prompt = item["capability"], item["prompt"]
                body = {
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                try:
                    t0 = time.perf_counter()
                    resp = await client.post(
                        f"{self.relay_url}/v1/messages",
                        json=body,
                        headers=headers,
                    )
                    latency_ms = (time.perf_counter() - t0) * 1000
                    latencies.append(latency_ms)

                    if resp.status_code == 200:
                        j = resp.json()
                        usage = j.get("usage", {}) or {}
                        out_tokens = usage.get("output_tokens", 0)
                        total_tokens += out_tokens
                        content = (j.get("content", []) or [{}])[0]
                        text_val = content.get("text", "") if isinstance(content, dict) else ""
                        quality = _score_quality(cap, text_val)
                        scores[cap] = round(quality, 2)
                    else:
                        scores[cap] = 0.0
                except Exception as e:
                    logger.warning("Benchmark failed for %s/%s: %s", model_name, cap, e)
                    scores[cap] = 0.0
                    latencies.append(0.0)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        avg_tps = total_tokens / (avg_latency / 1000) if avg_latency > 0 else 0.0

        return {
            "coding": scores.get("coding", 0.0),
            "analysis": scores.get("analysis", 0.0),
            "reasoning": scores.get("reasoning", 0.0),
            "instruction_following": scores.get("instruction_following", 0.0),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_tokens_per_sec": round(avg_tps, 2),
        }

    async def generate_swot(
        self, model_name: str, benchmark_results: dict[str, Any]
    ) -> dict[str, Any]:
        """Use the model to generate SWOT analysis from benchmark results."""
        prompt = f"""Analyze these benchmark results for the LLM model "{model_name}"
and produce a SWOT analysis.

Benchmark results:
{json.dumps(benchmark_results, indent=2)}

Respond in valid JSON only, with these exact keys:
- strengths: string (2-3 bullet points)
- weaknesses: string (2-3 bullet points)
- opportunities: string (2-3 bullet points)
- threats: string (2-3 bullet points)
- recommended_roles: list of strings (e.g. ["data-scientist", "research-analyst"])
"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.anthropic_auth_token}",
            "anthropic-version": "2023-06-01",
            "x-acorn-model": model_name,
        }
        body = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.relay_url}/v1/messages",
                    json=body,
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning("SWOT generation failed: %d", resp.status_code)
                    return _default_swot(benchmark_results)

                j = resp.json()
                content = (j.get("content", []) or [{}])[0]
                text_val = content.get("text", "") if isinstance(content, dict) else ""
                return _parse_swot_response(text_val, benchmark_results)
        except Exception as e:
            logger.exception("SWOT generation error: %s", e)
            return _default_swot(benchmark_results)

    async def recommend_model(
        self, task_type: str, role: str, db_session: AsyncSession
    ) -> str:
        """Query model_registry for best model given task_type and role."""
        result = await db_session.execute(
            text("""
                SELECT name, benchmark_scores, success_rate, recommended_roles
                FROM model_registry
                WHERE is_available = TRUE
                  AND name NOT LIKE '%embed%'
                  AND (benchmark_scores IS NOT NULL AND benchmark_scores != '{}')
            """),
        )
        rows = result.mappings().all()
        if not rows:
            return settings.coder_model

        weights = _TASK_TYPE_WEIGHTS.get(
            task_type,
            {"coding": 0.25, "analysis": 0.25, "reasoning": 0.25, "instruction_following": 0.25},
        )

        best_name = ""
        best_score = -1.0

        for row in rows:
            name = row["name"]
            scores = row["benchmark_scores"] or {}
            if isinstance(scores, str):
                try:
                    scores = json.loads(scores)
                except Exception:
                    scores = {}
            success_rate = float(row["success_rate"] or 0.0)
            recommended = row["recommended_roles"] or []

            weighted = sum(
                float(scores.get(k, 0) or 0) * w
                for k, w in weights.items()
            )
            score = weighted * 0.7 + success_rate * 0.3
            if role in recommended:
                score += 0.2
            if score > best_score:
                best_score = score
                best_name = name

        return best_name or settings.coder_model

    async def store_benchmark_results(
        self,
        db_session: AsyncSession,
        model_name: str,
        benchmark_results: dict[str, Any],
        swot: dict[str, Any],
    ) -> None:
        """Store benchmark and SWOT in model_registry."""
        scores = {
            "coding": benchmark_results.get("coding", 0),
            "analysis": benchmark_results.get("analysis", 0),
            "reasoning": benchmark_results.get("reasoning", 0),
            "instruction_following": benchmark_results.get("instruction_following", 0),
        }
        rec_roles = list(swot.get("recommended_roles", []) or [])
        await db_session.execute(
            text("""
                UPDATE model_registry SET
                    benchmark_scores = CAST(:scores AS jsonb),
                    avg_latency_ms = :avg_latency_ms,
                    avg_tokens_per_sec = :avg_tokens_per_sec,
                    strengths = :strengths,
                    weaknesses = :weaknesses,
                    opportunities = :opportunities,
                    threats = :threats,
                    recommended_roles = :recommended_roles,
                    last_benchmarked_at = NOW(),
                    updated_at = NOW()
                WHERE name = :name
            """),
            {
                "name": model_name,
                "scores": json.dumps(scores),
                "avg_latency_ms": benchmark_results.get("avg_latency_ms", 0),
                "avg_tokens_per_sec": benchmark_results.get("avg_tokens_per_sec", 0),
                "strengths": swot.get("strengths"),
                "weaknesses": swot.get("weaknesses"),
                "opportunities": swot.get("opportunities"),
                "threats": swot.get("threats"),
                "recommended_roles": rec_roles,
            },
        )
        await db_session.execute(
            text("""
                INSERT INTO model_registry (id, name, provider, benchmark_scores, avg_latency_ms,
                    avg_tokens_per_sec, strengths, weaknesses, opportunities, threats,
                    recommended_roles, last_benchmarked_at, is_available, updated_at)
                SELECT :id, :name, 'ollama', CAST(:scores AS jsonb), :avg_latency_ms,  -- noqa: E501
                    :avg_tokens_per_sec,
                    :strengths, :weaknesses, :opportunities, :threats, :recommended_roles,
                    NOW(), TRUE, NOW()
                WHERE NOT EXISTS (SELECT 1 FROM model_registry WHERE name = :name)
            """),
            {
                "id": str(uuid4()),
                "name": model_name,
                "scores": json.dumps(scores),
                "avg_latency_ms": benchmark_results.get("avg_latency_ms", 0),
                "avg_tokens_per_sec": benchmark_results.get("avg_tokens_per_sec", 0),
                "strengths": swot.get("strengths"),
                "weaknesses": swot.get("weaknesses"),
                "opportunities": swot.get("opportunities"),
                "threats": swot.get("threats"),
                "recommended_roles": rec_roles,
            },
        )


def _to_pg_text_array(arr: list[str]) -> str:
    """Convert Python list to PostgreSQL text[] literal."""
    if not arr:
        return "{}"
    escaped = ('"' + str(x).replace("\\", "\\\\").replace('"', '\\"') + '"' for x in arr)
    return "{" + ",".join(escaped) + "}"


def _score_instruction_following(text: str) -> float:
    clean = text.strip().lower()
    if clean == "hello":
        return 1.0
    if "hello" in clean and len(clean) < 20:
        return 0.8
    return 0.3


def _score_coding(text: str) -> float:
    if "def " in text and ("fib" in text.lower() or "fibonacci" in text.lower()):
        return 1.0
    return 0.8 if "def " in text else 0.5


def _score_analysis(text: str) -> float:
    if any(w in text.lower() for w in ["trend", "increase", "decrease", "growth"]):
        return 1.0
    return 0.7 if len(text) > 50 else 0.5


def _score_reasoning(text: str) -> float:
    if "yes" in text.lower() or "all a are c" in text.lower():
        return 1.0
    if "transitive" in text.lower() or "syllogism" in text.lower():
        return 0.9
    return 0.7 if len(text) > 30 else 0.5


def _score_quality(capability: str, text: str) -> float:
    """Simple heuristics for quality score."""
    if not text or len(text.strip()) < 5:
        return 0.0
    scorers = {
        "instruction_following": _score_instruction_following,
        "coding": _score_coding,
        "analysis": _score_analysis,
        "reasoning": _score_reasoning,
    }
    fn = scorers.get(capability)
    return fn(text) if fn else (0.7 if len(text) > 30 else 0.5)


def _parse_swot_response(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON from model response."""
    text = text.strip()
    for start in ("```json", "```"):
        if text.startswith(start):
            text = text[len(start) :].lstrip()
        if text.endswith("```"):
            text = text[:-3].rstrip()
    try:
        data = json.loads(text)
        return {
            "strengths": str(data.get("strengths", "")),
            "weaknesses": str(data.get("weaknesses", "")),
            "opportunities": str(data.get("opportunities", "")),
            "threats": str(data.get("threats", "")),
            "recommended_roles": list(data.get("recommended_roles", [])),
        }
    except Exception:
        return _default_swot(fallback)


def _default_swot(benchmark: dict[str, Any]) -> dict[str, Any]:
    """Fallback SWOT when parsing fails."""
    return {
        "strengths": "Benchmark completed.",
        "weaknesses": "Could not generate detailed analysis.",
        "opportunities": "Consider fine-tuning for specific tasks.",
        "threats": "Competition from specialized models.",
        "recommended_roles": [],
    }
