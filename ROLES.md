# ACORN Agent Roles — Manifest-to-Runtime Mapping

This document maps the 9 agent names defined in MANIFEST.md Part I to the
runtime role slugs used in `VALID_ROLES` (`api/routers/agents.py`) and the
Claude agent definition files under `.claude/agents/`.

| Manifest Name        | Runtime Slug          | Agent File                         | Description |
|----------------------|-----------------------|------------------------------------|-------------|
| Orchestrator         | `orchestrator`        | `.claude/agents/orchestrator.md`   | Problem framing, task decomposition, agent coordination |
| Research Analyst     | `data-scientist`      | `.claude/agents/data-scientist.md` | EDA, statistical analysis, hypothesis testing |
| Synthesis Agent      | `software-architect`  | `.claude/agents/software-architect.md` | Assembles outputs into cohesive deliverables |
| Domain Specialist    | `data-engineer`       | `.claude/agents/data-engineer.md`  | Data ingestion, pipeline construction, schema design |
| Validator            | `reviewer`            | *(inline in harness)*              | Code review, output quality checks |
| Judge                | `judge-agent`         | `.claude/agents/judge-agent.md`    | Final verdict (pass/fail) with check matrix |
| Kernel Extractor     | `kernel-extractor`    | `.claude/agents/kernel-extractor.md` | Post-PASS pattern extraction to probationary grove |
| Interface Agent      | `frontend`            | `.claude/agents/frontend.md`       | UI/dashboard generation |
| Calibration Agent    | `meta-agent`          | `.claude/agents/meta-agent.md`     | Prompt evolution, benchmark-driven deprecation |

## Additional Runtime Roles

These roles extend the Manifest's core 9 for operational flexibility:

| Runtime Slug    | Agent File                      | Purpose |
|-----------------|---------------------------------|---------|
| `ml-engineer`   | `.claude/agents/ml-engineer.md` | Model training, feature engineering, inference |
| `coder`         | *(inline in harness)*           | General-purpose coding tasks |
| `ai-engineer`   | `.claude/agents/ai-engineer.md` | AI/ML integration, embedding pipelines |
| `devops`        | `.claude/agents/devops.md`      | Infrastructure, Docker, CI/CD |
| `security-expert` | `.claude/agents/security-expert.md` | Security audit, vulnerability scanning |
