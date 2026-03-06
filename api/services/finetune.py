"""Fine-tune Ollama models using Modelfile-style customization (system prompts + parameters)."""
__pattern__ = "Strategy"

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings

logger = logging.getLogger(__name__)


class FinetuneService:
    """Fine-tune Ollama models using Modelfiles and custom datasets."""

    def __init__(self) -> None:
        self.ollama_url = settings.ollama_base_url.rstrip("/")
        self.relay_url = settings.anthropic_base_url.rstrip("/")
        self.coder_model = settings.coder_model

    async def create_finetuned_model(  # noqa: C901
        self,
        base_model: str,
        dataset_path: str,
        model_name: str,
        system_prompt: str = "",
    ) -> dict[str, Any]:
        """Create a fine-tuned model using Ollama's create API.

        Ollama doesn't support traditional fine-tuning, but supports customization via:
        1. Read the dataset file to extract domain-specific examples
        2. Generate a system prompt that embeds domain knowledge from the dataset
        3. POST to {ollama_url}/api/create with from, system, and parameters

        The key insight: we "fine-tune" by creating specialized system prompts
        that embed domain-specific knowledge and examples from datasets.
        """
        try:
            domain_examples = ""
            path = Path(dataset_path)
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        lines = f.readlines()[:20]
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                q = obj.get("prompt") or obj.get("question") or obj.get("input", "")
                                a = obj.get("response") or obj.get("answer") or obj.get("output", "")  # noqa: E501
                                if q and a:
                                    domain_examples += f"\nQ: {q[:500]}\nA: {a[:500]}\n"
                            elif isinstance(obj, str):
                                domain_examples += f"\n{obj[:300]}\n"
                        except json.JSONDecodeError:
                            domain_examples += f"\n{line[:300]}\n"
                except OSError as e:
                    logger.warning("Could not read dataset %s: %s", dataset_path, e)

            system = system_prompt or "You are a domain-specialized assistant."
            if domain_examples:
                system += "\n\nDomain-specific examples:\n" + domain_examples

            body: dict[str, Any] = {
                "model": model_name,
                "from": base_model,
                "system": system,
                "parameters": {"temperature": 0.7, "top_p": 0.9},
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(f"{self.ollama_url}/api/create", json=body)
                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Ollama create failed: {resp.status_code} {resp.text[:200]}",
                    }
                data = resp.json() if resp.content else {}
                return {
                    "success": True,
                    "model_name": model_name,
                    "base_model": base_model,
                    "status": data.get("status", "created"),
                }
        except Exception as e:
            logger.exception("create_finetuned_model failed")
            return {"success": False, "error": str(e)}

    async def create_domain_specialist(
        self,
        base_model: str,
        domain: str,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Create a domain-specialized model by querying domain_knowledge table."""
        try:
            result = await db_session.execute(
                text("""
                    SELECT content FROM domain_knowledge
                    WHERE domain = :domain
                    ORDER BY created_at DESC
                    LIMIT 20
                """),
                {"domain": domain},
            )
            rows = result.mappings().all()
            knowledge_parts = [r["content"] for r in rows if r.get("content")]

            system = (
                f"You are a domain expert in {domain}. "
                "Use the following knowledge to inform your responses:\n\n"
            )
            for i, k in enumerate(knowledge_parts[:15], 1):
                system += f"{i}. {k[:800]}\n\n"

            model_name = f"{base_model}-{domain}-specialist"

            body: dict[str, Any] = {
                "model": model_name,
                "from": base_model,
                "system": system,
                "parameters": {"temperature": 0.7, "top_p": 0.9},
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(f"{self.ollama_url}/api/create", json=body)
                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Ollama create failed: {resp.status_code} {resp.text[:200]}",
                    }

            await db_session.execute(
                text("""
                    INSERT INTO model_registry
                    (id, name, provider, is_finetuned, base_model, is_available, updated_at)
                    VALUES (:id, :name, 'ollama', TRUE, :base_model, TRUE, NOW())
                    ON CONFLICT (name) DO UPDATE SET
                        is_finetuned = TRUE,
                        base_model = EXCLUDED.base_model,
                        is_available = TRUE,
                        updated_at = NOW()
                """),
                {"id": str(uuid4()), "name": model_name, "base_model": base_model},
            )
            await db_session.commit()

            return {
                "success": True,
                "model_name": model_name,
                "base_model": base_model,
                "domain": domain,
                "knowledge_items": len(knowledge_parts),
            }
        except Exception as e:
            logger.exception("create_domain_specialist failed")
            await db_session.rollback()
            return {"success": False, "error": str(e)}

    async def list_finetuned_models(self, db_session: AsyncSession) -> list[dict[str, Any]]:
        """List all fine-tuned models from model_registry WHERE is_finetuned = TRUE."""
        try:
            result = await db_session.execute(
                text("""
                    SELECT name, base_model, finetune_dataset, created_at, updated_at
                    FROM model_registry
                    WHERE is_finetuned = TRUE
                    ORDER BY updated_at DESC
                """)
            )
            rows = result.mappings().all()
            return [
                {
                    "name": r["name"],
                    "base_model": r["base_model"],
                    "finetune_dataset": r["finetune_dataset"],
                    "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                    "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.exception("list_finetuned_models failed: %s", e)
            return []

    async def generate_training_data(  # noqa: C901
        self,
        domain: str,
        db_session: AsyncSession,
    ) -> str:
        """Generate synthetic training examples for a domain.
        1. Query domain_knowledge for the domain
        2. Use an LLM to generate Q&A pairs based on the knowledge
        3. Format as a dataset
        4. Save to /workspace/datasets/{domain}_training.jsonl
        5. Return the path
        """
        try:
            result = await db_session.execute(
                text("""
                    SELECT content FROM domain_knowledge
                    WHERE domain = :domain
                    ORDER BY created_at DESC
                    LIMIT 15
                """),
                {"domain": domain},
            )
            rows = result.mappings().all()
            knowledge = "\n\n".join(r["content"][:2000] for r in rows if r.get("content"))

            if not knowledge:
                return ""

            prompt = f"""Based on the following domain knowledge about {domain}, generate 10 Q&A pairs.

Format each as a JSON object on its own line:
{{"prompt": "question here", "response": "answer here"}}

Domain knowledge:
{knowledge[:6000]}

Generate exactly 10 Q&A pairs, one JSON per line. No other text."""  # noqa: E501

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.relay_url}/v1/messages",
                    json={
                        "model": "claude-sonnet-4-6",
                        "max_tokens": 2048,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.anthropic_auth_token}",
                        "anthropic-version": "2023-06-01",
                        "x-acorn-model": self.coder_model,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("LLM call failed: %s %s", resp.status_code, resp.text[:200])
                    return ""

                data = resp.json()
                content_blocks = data.get("content", []) or [{}]
                text_content = content_blocks[0].get("text", "") if content_blocks else ""

            examples: list[dict[str, str]] = []
            for line in text_content.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("```"):
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and ("prompt" in obj or "question" in obj):
                        q = obj.get("prompt") or obj.get("question", "")
                        a = obj.get("response") or obj.get("answer", "")
                        if q and a:
                            examples.append({"prompt": q, "response": a})
                except json.JSONDecodeError:
                    continue

            if not examples:
                return ""

            datasets_dir = Path(settings.acorn_workspace_base) / "datasets"
            datasets_dir.mkdir(parents=True, exist_ok=True)
            output_path = datasets_dir / f"{domain}_training.jsonl"

            with open(output_path, "w", encoding="utf-8") as f:
                for ex in examples:
                    f.write(json.dumps(ex, ensure_ascii=False) + "\n")

            return str(output_path)
        except Exception as e:
            logger.exception("generate_training_data failed: %s", e)
            return ""
