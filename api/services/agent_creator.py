__pattern__ = "Factory"

import logging
from pathlib import Path
from typing import Any

import httpx

from api.config import settings

logger = logging.getLogger(__name__)

AGENT_TEMPLATE = '''---
name: {name}
description: {description}
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__acorn-memory
  - mcp__filesystem
---

# {title}

## Identity

{identity}

## Lifecycle

1. RESTORE, ORIENT, KERNEL QUERY
2. **EXECUTE** - {execute_description}
3. **REPORT** - {report_description}
4. CLOSE, SAVE

## Output Contract

{output_contract}

## Constraints

{constraints}
'''


class AgentCreator:
    """Dynamically creates agent definition files."""

    def __init__(self, agents_dir: str) -> None:
        self.agents_dir = Path(agents_dir)

    def create_agent(
        self,
        name: str,
        description: str,
        identity: str,
        execute_description: str,
        report_description: str,
        output_contract: str,
        constraints: str,
    ) -> dict[str, Any]:
        """Create a new agent definition .md file."""
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.agents_dir / f"{name}.md"

        if filepath.exists():
            return {"created": False, "reason": "already_exists", "path": str(filepath)}

        title = name.replace("-", " ").title()
        content = AGENT_TEMPLATE.format(
            name=name,
            description=description,
            title=title,
            identity=identity,
            execute_description=execute_description,
            report_description=report_description,
            output_contract=output_contract,
            constraints=constraints,
        )

        filepath.write_text(content)
        logger.info("Created agent definition: %s", filepath)
        return {"created": True, "path": str(filepath)}

    async def write_orient_context(
        self, role: str, worktree_path: str,
    ) -> None:
        """Fetch GRS role context and write ORIENT_CONTEXT.md into the agent's worktree.

        This injects the top-3 recent wins and misses for the role so the agent
        knows what worked and what didn't before beginning work.
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"http://localhost:{settings.port}/api/rewards/role-context/{role}",
                )
                if resp.status_code != 200:
                    return
                ctx: dict[str, Any] = resp.json()
        except Exception:
            logger.debug("ORIENT context fetch failed for role=%s (non-blocking)", role)
            return

        wins = ctx.get("recent_wins", [])
        misses = ctx.get("recent_misses", [])
        score = ctx.get("score", {})

        lines = [
            f"# ORIENT Context — {role}",
            "",
            "## Recent Wins (what earned rewards)",
        ]
        if wins:
            for w in wins[:3]:
                lines.append(f"- **{w['signal']}** (+{w['points']} pts): {w.get('rationale', '')}")
        else:
            lines.append("- No recent wins recorded yet.")

        lines += ["", "## Recent Misses (what caused penalties)"]
        if misses:
            for m in misses[:3]:
                lines.append(f"- **{m['signal']}** ({m['points']} pts): {m.get('rationale', '')}")
        else:
            lines.append("- No recent penalties recorded.")

        lines += [
            "",
            "## Score",
            f"- Cumulative: {score.get('cumulative', 0)} pts",
            f"- Rolling 30d: {score.get('rolling_30d', 0)} pts",
            f"- Problems contributed: {score.get('problems', 0)}",
            "",
            "> Read this file at the start of your session (ORIENT step) to calibrate behaviour.",
        ]

        wt = Path(worktree_path)
        wt.mkdir(parents=True, exist_ok=True)
        orient_file = wt / "ORIENT_CONTEXT.md"
        orient_file.write_text("\n".join(lines))
        logger.info("Wrote ORIENT_CONTEXT.md for role=%s at %s", role, orient_file)

    def list_agents(self) -> list[dict[str, str]]:
        """List all agent definitions."""
        if not self.agents_dir.exists():
            return []

        agents = []
        for f in sorted(self.agents_dir.glob("*.md")):
            agents.append({
                "name": f.stem,
                "path": str(f),
            })
        return agents
