__pattern__ = "Factory"

import logging
from pathlib import Path
from typing import Any

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
