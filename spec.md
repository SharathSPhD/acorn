# OAK — Orchestrated Agent Kernel
## Project Specification v1.2

> *Deep-rooted in local compute, branching into limitless agent groves, growing stronger with every problem solved.*
>
> Remote repository: **https://github.com/SharathSPhD/oak.git**
> Primary platform: **NVIDIA DGX Spark** (ports to Mac Mini M4 and cloud GPU)
> Initiated via: **Claude Code agent teams**

**v1.1 Amendment (harness.md):** Incorporated the OAK Harness architecture — `claude-harness` Docker container with sandboxed tool proxy, Redis session state, and `oak-api-proxy` dynamic routing layer. Updated Ollama+Claude Code environment variable recipe and model names. Changes in Sections 1.2, 4.1, 4.6 (new), 5.1, 7, and 13.

**v1.2 Amendment (critique-driven):** Rewrote Section 1.1 as measurable outcome objectives (separating goals from implementation choices). Updated Section 1.2 scaling principle to acknowledge configurable resource caps. Added Section 1.3 (Self-Evolution Boundaries) and Section 1.4 (Mandatory vs Optional). Added harness/proxy risk mitigations to Section 4.6. Added `MAX_AGENTS_PER_PROBLEM`, `MAX_CONCURRENT_PROBLEMS`, `MAX_HARNESS_CONTAINERS` to Section 5.4. Added SLO-style exit criteria to all roadmap phases (Section 14). Added Section 16 (Observability) and Section 17 (Failure Mode Reference).

---

## 1. Project Overview and Objectives

OAK is a self-evolving AI software factory. It ingests raw problems — described in natural language, accompanied by data files or database connections — and produces tailored analytical dashboards and applications via dynamic teams of specialist AI agents. Every problem OAK solves teaches it something permanent. The system accumulates executable skills, refines its agent prompts from telemetry, and evolves its own UI as new capability classes are mastered. There is no fixed solution template and no finite capability ceiling.

The name is deliberate. An oak tree does not pre-plan its final shape; it grows in response to its environment, putting down deeper roots as it encounters harder ground, branching freely where there is light. OAK the system is the same: agent roles emerge from problem complexity rather than being fixed in advance, memory accumulates like growth rings, and the UI canopy expands as the agent grove below it matures.

### 1.1 Core Objectives

OAK's objectives are stated as measurable outcomes. The *how* — PostgreSQL, Streamlit/Dash, the tripartite memory architecture, the Voyager pattern, the OAK Harness — are design choices that serve these outcomes and may evolve independently.

- **Autonomous problem-to-app conversion.** Given heterogeneous data and a natural-language goal, OAK must produce a deployed, usable analytical application with minimal human intervention — no hand-holding through individual analysis steps, no manual model selection. For any new problem type, OAK must complete a full end-to-end cycle (ingest → analyse → model → synthesise → validate → deploy) with zero runtime errors on basic user flows.

- **Compounding skill reuse.** For recurring problem classes, the median time-to-first-useful-app must decrease by at least 50% after three similar problems have been solved, as measured via the `agent_telemetry` table. Skill reuse — not re-derivation — is the mechanism. Skills that cannot demonstrate reuse across at least two independent problems must not be promoted to permanent status.

- **Self-evolving interface.** The Hub UI must reflect OAK's current capability set. New problem classes that are mastered cause new pages or widgets to appear in the Hub via automated PRs reviewed and merged by the human operator. The interface is never manually updated by the operator for capability reasons.

- **Data sovereignty.** All problem data, agent memory, compiled skills, and learned patterns must remain on operator-owned hardware at all times. Cloud escalation (Claude API) is strictly optional, stateless, and never retains problem context server-side. The system must function fully with no external API key.

- **Platform portability.** OAK must run identically on DGX Spark, Mac Mini M4 Pro, and cloud GPU instances using only a single environment variable change (`OAK_MODE`). No application code changes are permitted between platforms.

### 1.2 Design Principles

**Sovereign compute.** No problem data, agent memory, or compiled skills leave the DGX Spark node. The system's growing intelligence is the operator's property. Claude API calls are optional escalation paths; the default inference path is entirely local via Ollama.

**Resource-aware scaling.** Agent count is not fixed at four, but it is not unconstrained either. The Orchestrator spawns as many agents as the problem requires — five for a simple ETL task, up to the configured maximum for a complex multi-modal forecasting problem. Two configurable caps (`MAX_AGENTS_PER_PROBLEM`, `MAX_CONCURRENT_PROBLEMS`) prevent resource exhaustion on any platform; these are tuning knobs, not architectural philosophy. Roles emerge from problem decomposition rather than being declared in advance.

**No security overhead.** OAK uses simple Docker network isolation. There are no OpenClaw components (which carry documented RCE and prompt-injection vulnerabilities), no third-party messaging integrations (no Slack, no WhatsApp, no email hooks), and no complex authentication layers. The system is designed for a single trusted operator on a private network.

**Portability by design.** A single `OAK_MODE` environment variable switches the Docker Compose configuration between `dgx`, `mini`, and `cloud` profiles. No code changes are required to port between platforms.

**Sandboxed harness.** Claude Code does not run loose on the host. Every agent session runs inside a dedicated `claude-harness` Docker container that sandboxes the Claude Code binary, intercepts all tool calls through a deny-list proxy before execution, and maintains persistent session state in Redis — giving agents the stateful terminal context that OpenClaw would have provided, without any of OpenClaw's RCE or prompt-injection exposure. All API calls from Claude Code are routed through a lightweight `oak-api-proxy` container that dynamically switches between the local Ollama endpoint and the Claude API based on per-call confidence, with no static configuration change required.

### 1.3 Self-Evolution Boundaries

OAK changes itself autonomously in some ways and only with human approval in others. This boundary is load-bearing: without it, the system can drift into states the operator cannot understand or safely reverse.

**What OAK changes autonomously (no human approval required):**
- Promotes skills from `probationary` to `permanent` after two verified independent uses.
- Generates and executes agent task plans within the current problem scope.
- Writes session state, telemetry, episodic memory, and judge verdicts without approval.
- Spawns and terminates agent sessions within the configured resource caps.

**What requires a PR and human merge before taking effect:**
- New Hub pages or widget additions (opened by Software Architect against `oak/ui`), subject to a churn limit: no more than 1 new UI PR per 3 problems solved without a human-triggered Hub architecture review. The total distinct Hub page count must not exceed 20 without explicit operator approval of a Hub restructure. Tabs added to existing pages do not count toward the page limit but are still subject to the per-3-problems rate.
- Agent prompt amendments (opened by Meta Agent against `oak/agents`).
- Any change to the Judge Agent's validation rules or the tool-proxy deny-list patterns.
- Deprecation of permanent skills.

**What requires explicit operator action (no automation path):**
- Schema migrations to existing tables.
- Changes to the TRUNK API surface or Docker Compose files.
- Changes to the resource cap variables (`MAX_AGENTS_PER_PROBLEM`, etc.).
- Deletion of problem worktrees before the 30-day archive window.

### 1.4 Mandatory vs Optional (v1 Scope)

Not all capabilities described in this spec are required for a functional v1. Attempting to build everything simultaneously is the most reliable path to a half-working system.

**Mandatory for v1 (Phases 0–3):**
- **TRUNK:** FastAPI with all five routers (`problems`, `agents`, `tasks`, `skills`, `telemetry`) and WebSocket stream.
- **GROVE:** Orchestrator, Data Engineer, Data Scientist, Judge Agent — four agents minimum. ML Engineer and Software Architect are optional for v1 (manual synthesis is acceptable).
- **ROOTS:** Full PostgreSQL schema; Redis for working memory and session state; filesystem skill library.
- **OAK Harness:** `claude-harness` container with tool proxy and Redis session state. Stall-based Claude API escalation is *disabled by default* — the proxy passes through to Ollama unconditionally until Phase 4 hardening.
- **Streamlit Hub:** Pages 01–05 (new problem, status, gallery, skill library, telemetry).
- **Skill library:** ETL category skills; probationary queue; basic promotion logic.

**Optional / v1.1+:**
- Meta Agent automated prompt rewrite (can be done manually in v1).
- Stall detection heuristics and Claude API escalation in the proxy.
- Plotly Dash spoke support (Streamlit-only is sufficient for v1).
- Software Architect UI evolution PRs (Hub pages can be seeded manually in v1).
- vLLM replacement for Ollama; Kubernetes overlay; cloud multi-GPU scaling.
- Concurrent problem support beyond one active problem at a time (DGX-only in v1).

---

## 2. System Architecture

The system is organised into six named layers, each with clear responsibilities and boundaries.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CANOPY  — UI Hub (Streamlit / Plotly Dash)                             │
│  Hosted: Streamlit Cloud / Render / Vercel (free tier)                  │
│  Problem submission · Live agent stream · Solution gallery · Metrics    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  REST + WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  TRUNK  — API Gateway (FastAPI + uvicorn, port 8000)                    │
│  /api/problems  /api/agents  /api/tasks  /api/skills  /api/telemetry    │
│  WS: /ws/stream/{problem_id}                                            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  GROVE  — Agent Engine                                                  │
│  oak-harness containers (one per agent session)                         │
│  Claude Code binary · tool-proxy · Redis session state                  │
│  Orchestrator  →  spawns N specialist agents dynamically                │
│  Data Engineer · Data Scientist · ML Engineer · Software Architect      │
│  Judge Agent · Skill Extractor · Meta Agent (async)                     │
│  Coordination: Shared Task List (PostgreSQL) + Mailbox (Redis pub/sub)  │
│  Hooks: PreToolUse · PostToolUse · TaskCompleted · TeammateIdle         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  All Claude Code API calls
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  HARNESS PROXY  — oak-api-proxy (FastAPI, port 9000)                   │
│  Dynamic routing: local Ollama ←→ Claude API (per-call confidence)      │
│  Logs every routing decision to telemetry                               │
└──────────┬────────────────────────────────────┬────────────────────────┘
           │ default (local)                    │ escalation (optional)
           ▼                                    ▼
┌──────────────────────┐            ┌───────────────────────┐
│  oak-ollama          │            │  api.anthropic.com     │
│  port 11434          │            │  (if API key set)      │
│  qwen3-coder         │            │  Sonnet / Haiku / Opus │
│  glm-4.7             │            └───────────────────────┘
│  llama3.3:70b        │
│  deepseek-v3         │
└──────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ROOTS  — Persistence (PostgreSQL 16 + pgvector · Redis 7)              │
│  L1 Working Memory: Redis (TTL-scoped, per session + harness state)     │
│  L2 Episodic Memory: PostgreSQL + pgvector (semantic retrieval)         │
│  L3 Procedural Memory: SKILL.md filesystem + PostgreSQL index           │
│  Task List · Mailbox · Telemetry · Problem Data · Agent Profiles        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SOIL  — Hardware                                                        │
│  DGX Spark (GB10 Grace Blackwell, 128GB unified, ~1 PFLOP)              │
│  → Mac Mini M4 Pro 64GB   → RunPod / DigitalOcean multi-GPU             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Orchestration boundary (hard rule).** The TRUNK and below own all computation, coordination, data, and intelligence. The CANOPY UI is a thin consumer of TRUNK API endpoints; it holds no agent logic and no problem data. The only state the CANOPY maintains locally is the user's browser session.

---

## 3. Repository Structure and Git Worktrees

OAK uses Git worktrees to give each concern an isolated filesystem view while sharing a single repository history. This is load-bearing for Claude Code agent teams: agents writing solution code in `oak/problem-{uuid}` cannot interfere with agents writing skill definitions in `oak/skills`, even if both are running simultaneously.

### 3.1 Branch Map

| Branch | Worktree path | Purpose |
|---|---|---|
| `main` | `~/oak/` | Stable core: Docker configs, schema DDL, FastAPI, shared libs |
| `oak/agents` | `~/oak-workspaces/agents/` | Agent definitions, CLAUDE.md per agent, hook scripts |
| `oak/skills` | `~/oak-workspaces/skills/` | Skill library: SKILL.md files, Python modules, probationary queue |
| `oak/ui` | `~/oak-workspaces/ui/` | Streamlit Hub, Dash components, static assets |
| `oak/problem-{uuid}` | `~/oak-workspaces/problem-{uuid}/` | Per-problem isolated workspace (created dynamically at problem start) |

### 3.2 Directory Layout (main branch)

```
~/oak/
├── .claude/
│   ├── CLAUDE.md               # Root Claude Code project config
│   ├── agents/                 # Subagent definition files
│   │   ├── orchestrator.md
│   │   ├── data-engineer.md
│   │   ├── data-scientist.md
│   │   ├── ml-engineer.md
│   │   ├── software-architect.md
│   │   ├── judge-agent.md
│   │   ├── skill-extractor.md
│   │   └── meta-agent.md
│   ├── hooks/                  # Lifecycle hook scripts
│   │   ├── pre-tool-use.sh     # 2nd-layer deny-list (after tool-proxy)
│   │   ├── post-tool-use.sh    # Telemetry + session state updates
│   │   ├── task-completed.sh   # Triggers skill extraction on pass
│   │   └── teammate-idle.sh    # Re-focus injection on idle
│   ├── mcp.json                # MCP server configurations
│   └── settings.json           # Claude Code project settings
├── docker/
│   ├── claude-harness/         # ← NEW: OAK Harness Docker image
│   │   ├── Dockerfile          # Claude Code + tool-proxy + session-state
│   │   └── scripts/
│   │       ├── tool-proxy.sh   # 1st-layer deny-list interceptor
│   │       └── session-state.py# Redis persistent terminal state
│   ├── docker-compose.dgx.yml
│   ├── docker-compose.mini.yml
│   ├── docker-compose.cloud.yml
│   └── docker-compose.base.yml # Shared service definitions
├── api/                        # FastAPI application
│   ├── main.py
│   ├── routers/
│   │   ├── problems.py
│   │   ├── agents.py
│   │   ├── tasks.py
│   │   ├── skills.py
│   │   └── telemetry.py
│   ├── models/                 # Pydantic schemas
│   ├── db/
│   │   ├── schema.sql          # Full DDL
│   │   └── connection.py
│   └── ws/
│       └── stream.py           # WebSocket manager
├── memory/                     # Memory utilities
│   ├── episodic.py             # pgvector retrieval
│   ├── skills.py               # Skill library operations
│   └── redis_client.py
├── oak_mcp/                    # Custom MCP servers
│   ├── oak-api-proxy/          # ← NEW: Dynamic routing proxy (port 9000)
│   │   ├── main.py             # FastAPI proxy: Ollama ↔ Claude API routing
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── oak-memory-mcp/         # pgvector semantic retrieval MCP
│   └── oak-skills-mcp/         # Skill library lookup MCP
├── scripts/
│   ├── bootstrap.sh            # Full DGX setup sequence (builds harness + proxy)
│   ├── new-problem.sh          # Creates worktree + launches harness container
│   └── merge-solution.sh       # Merges problem branch → main after validation
└── README.md
```

---

## 4. Claude Code Scaffolding

This section defines everything Claude Code reads and executes. Every file here must exist before the first `claude` session is started.

### 4.1 Root CLAUDE.md

The root `CLAUDE.md` is the single most important file — Claude Code reads it first and uses it to understand the project, available tools, and operational rules.

```markdown
# OAK — Orchestrated Agent Kernel

You are operating within the OAK system on a NVIDIA DGX Spark node.
OAK_MODE is set to: ${OAK_MODE} (dgx | mini | cloud)

## Runtime Environment (Critical)
Claude Code connects to local models via these environment variables —
they are set by the claude-harness container and must NOT be overridden:

  ANTHROPIC_BASE_URL=http://oak-api-proxy:9000   # OAK dynamic routing proxy
  ANTHROPIC_AUTH_TOKEN=ollama                     # Required for Ollama compat
  ANTHROPIC_API_KEY=                              # Explicitly empty; proxy manages real key

To invoke: claude --model qwen3-coder --workspace /workspace
Alternative models: glm-4.7 (analysis), llama3.3:70b (reasoning)

The oak-api-proxy routes each call to Ollama or Claude API automatically
based on task type and response confidence. You do not need to manage this.

## Your Role
When invoked as Team Lead, your job is to:
1. Read the problem statement and data manifest from the current problem worktree.
2. Decompose the problem into tasks using TaskCreate.
3. Spawn specialist teammates for each task class.
4. Monitor the shared task list and synthesise outputs.
5. Invoke the Judge Agent before any solution is marked complete.

## Environment
- API proxy (your Anthropic endpoint): http://oak-api-proxy:9000
- Ollama (local models): http://oak-ollama:11434
- PostgreSQL: postgresql://oak:oak@oak-postgres:5432/oak
- Redis: redis://oak-redis:6379 (also holds your session state)
- Skill library: ~/oak-workspaces/skills/
- Problem workspace: ~/oak-workspaces/problem-${PROBLEM_UUID}/

## Agent Team Setup
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
Team name convention: oak-${PROBLEM_UUID}
Task folder: ~/.claude/tasks/oak-${PROBLEM_UUID}/

## Available Subagents
See .claude/agents/ — invoke by name (e.g., `use agent data-engineer`).

## Session State
Your session state (open files, command history, git state) persists in Redis
under oak:session:${AGENT_ID}. The harness restores this at session start.
You do not need to re-establish context from scratch between invocations.

## MCP Servers
See .claude/mcp.json — filesystem, postgres, git, oak-memory, oak-skills are all available.

## Hooks
All hooks are in .claude/hooks/. They run automatically — do not disable them.
Note: hooks execute AFTER the tool-proxy layer in the claude-harness container.
The proxy catches dangerous commands first; hooks add OAK-specific logic.

## Rules
- Never drop tables or delete files without a pre-tool-use hook approval.
- Never commit to main directly — always use oak/problem-{uuid} branch.
- Always run the Judge Agent before marking a problem TaskCompleted.
- Log all tool invocations via the post-tool-use hook (automated).
- No third-party messaging. No external API calls except through oak-api-proxy.
```

### 4.2 MCP Server Configuration (.claude/mcp.json)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/home/oak", "/mnt/oak-data", "/mnt/oak-skills"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://oak:oak@oak-postgres:5432/oak"]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/home/oak"]
    },
    "oak-memory": {
      "command": "python3",
      "args": ["/home/oak/oak_mcp/oak-memory-mcp/server.py"]
    },
    "oak-skills": {
      "command": "python3",
      "args": ["/home/oak/oak_mcp/oak-skills-mcp/server.py"]
    }
  }
}
```

### 4.3 Subagent Definitions (.claude/agents/)

Each file in `.claude/agents/` defines a Claude Code subagent with a constrained persona and specific tool access. The format follows Claude Code's subagent spec: a markdown file with a YAML front-matter block.

**orchestrator.md** is the Team Lead. Its system prompt instructs it to decompose problems into typed tasks (ingest / analyse / model / synthesise / validate), assign them to appropriate specialist agents, monitor progress via the task list, and synthesise final output. It has read access to all worktrees and write access to the task list and mailbox.

**data-engineer.md** restricts the agent to ETL operations: reading raw files from `/mnt/oak-data/`, profiling columns (types, nulls, cardinality), generating DDL via the postgres MCP, and executing schema migrations. It is explicitly forbidden from writing application code or touching the UI worktree.

**data-scientist.md** focuses on analysis: running statistical profiles, generating pgvector embeddings via the oak-memory MCP, producing correlation matrices, and writing analysis reports to the problem worktree. It may invoke the postgres MCP for read operations but not DDL.

**ml-engineer.md** handles model selection and inference integration. It first queries the oak-skills MCP to find any matching skill (e.g., "time-series anomaly detection") before reasoning from scratch. It writes model code and inference scripts to the problem worktree.

**software-architect.md** synthesises all agent outputs into a Streamlit or Dash application. It reads analysis reports and model code from the problem worktree, generates `app.py` (the solution spoke), and commits it to the problem branch. It also generates any new Hub components required by this problem type and opens a PR to `oak/ui`.

**judge-agent.md** is the quality gate. It runs linting (`ruff`, `mypy`), schema validation, and a smoke-test suite against the generated application. It posts a structured verdict (PASS / FAIL + reasons) to the mailbox. If FAIL, the relevant agent is re-tasked. A task cannot be marked `TaskCompleted` until the judge posts PASS.

**skill-extractor.md** runs asynchronously after every PASS verdict. It reads the problem worktree, identifies reusable patterns, and writes candidate SKILL.md entries to the probationary queue in `~/oak-workspaces/skills/probationary/`. It also updates the skill index in PostgreSQL.

**meta-agent.md** runs on a schedule (daily, or after every 10 problems). It reads the telemetry table, identifies recurring friction points, and proposes updates to agent system prompts — opening PRs against the `oak/agents` branch for human review.

### 4.4 Skill Library (.claude/skills/ and ~/oak-workspaces/skills/)

OAK implements the Voyager pattern: successful solution patterns are compiled into executable skills that future agents retrieve rather than re-derive. A skill is a SKILL.md file plus an optional Python module. The SKILL.md follows this template:

```markdown
# Skill: {skill_name}
## Category: {etl | analysis | ml | ui | infra}
## Trigger keywords: {comma-separated terms for semantic retrieval}
## Verified on problems: {list of problem UUIDs}
## Status: {probationary | permanent}

## Description
Plain English description of what this skill does and when to use it.

## Prerequisites
Environment / library requirements.

## Implementation
```python
# The actual executable code block or procedure
```

## Known edge cases
List of failure modes and how they are handled.

## Do not use when
Explicit contra-indications.
```

Skills start in `skills/probationary/`. The Skill Extractor promotes a skill to `skills/permanent/` only after it has been successfully applied to at least two independent problems. This prevents noise accumulation from one-off solutions.

### 4.5 Lifecycle Hooks (.claude/hooks/)

Hooks intercept Claude Code's tool execution pipeline. They are shell scripts that receive tool context via environment variables and stdin.

**pre-tool-use.sh** runs before any tool invocation. For Bash commands containing `DROP`, `DELETE`, `rm -rf`, or `truncate`, it prints a warning, logs the attempted command, and exits with code 2 (blocking the tool call). For all other commands it exits 0.

**post-tool-use.sh** runs after every tool call. It inserts a row into the `agent_telemetry` table via `psql`, recording: `agent_id`, `tool_name`, `duration_ms`, `problem_uuid`, `timestamp`. This is the data the meta-agent analyses.

**task-completed.sh** fires when an agent attempts to close a task. It checks the PostgreSQL `tasks` table for a corresponding judge verdict. If no PASS verdict exists, it exits with code 2 (blocking closure) and appends a message instructing the agent to invoke the Judge Agent. If PASS exists, it triggers the skill-extractor agent asynchronously.

**teammate-idle.sh** fires if an agent session has produced no tool calls for more than 120 seconds. It injects a structured prompt: "You appear to be idle. Your current task is: {task description}. Last known state: {last tool output}. Please continue or flag a blocker."

### 4.6 OAK Harness (claude-harness container)

This section describes the most architecturally significant addition from harness.md: the `oak-harness` Docker container, which is the actual execution environment for every Claude Code agent session in OAK. Rather than running Claude Code loosely on the host or in a generic container, every agent runs inside `oak-harness` — a custom image that bundles the Claude Code binary alongside a tool-call proxy, Redis session state, and a dynamic API routing layer. This is how OAK gets OpenClaw's benefits (persistent terminal state, sandboxed execution) without any of OpenClaw's documented security liabilities.

#### Why the Harness Exists

Claude Code running on a bare host has two gaps: it is stateless between invocations (each session starts with no memory of open files or recent commands), and it has unrestricted access to the host filesystem and network. OpenClaw solves both by wrapping Claude Code in a persistent Dockerised terminal — but OpenClaw's exposed UI and prompt-injection attack surface introduce RCE risk that the security principle in §1.2 explicitly rules out. The OAK Harness solves the same problems differently: stateless Claude Code + Redis session state gives persistent context; a tool-call proxy + Docker network isolation gives the sandbox. The result is functionally equivalent to OpenClaw's dev experience with none of its exposure.

#### Dockerfile

```dockerfile
# docker/claude-harness/Dockerfile
FROM node:20-slim

# Claude Code binary (~100MB) — the full harness: subagents, skills,
# agent teams, hooks, MCP orchestration. All of this works against Ollama.
RUN npm install -g @anthropic-ai/claude-code

# Python for the tool proxy and Redis session state scripts
RUN apt-get update && apt-get install -y \
    python3 python3-pip git curl jq \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir redis psycopg2-binary requests fastapi uvicorn

# OAK-specific scripts
COPY scripts/tool-proxy.sh   /usr/local/bin/oak-tool-proxy
COPY scripts/session-state.py /usr/local/bin/oak-session
RUN chmod +x /usr/local/bin/oak-tool-proxy /usr/local/bin/oak-session

# All agent work is sandboxed to /workspace — no host filesystem access
WORKDIR /workspace

# These three variables are the canonical Ollama + Claude Code recipe.
# ANTHROPIC_BASE_URL points to the oak-api-proxy (not directly to Ollama)
# so the proxy can dynamically route to Ollama or Claude API per call.
# ANTHROPIC_API_KEY is intentionally empty — the proxy holds the real key.
ENV ANTHROPIC_BASE_URL=http://oak-api-proxy:9000
ENV ANTHROPIC_AUTH_TOKEN=ollama
ENV ANTHROPIC_API_KEY=

# Restore session state from Redis before starting, then invoke Claude Code.
# qwen3-coder is Ollama's recommended model for code-heavy agent tasks.
ENTRYPOINT ["/bin/sh", "-c", "python3 /usr/local/bin/oak-session restore && \
            exec claude --model qwen3-coder --workspace /workspace \"$@\""]
```

#### Tool Proxy (tool-proxy.sh)

The tool proxy intercepts every Bash and shell tool call that Claude Code attempts, before the `.claude/hooks/pre-tool-use.sh` hook fires. The proxy is the first line of defence; the hook is the second. Together they form two independent deny-list layers catching different threat classes.

```bash
#!/bin/bash
# scripts/tool-proxy.sh
# Called by Claude Code's tool execution pipeline for every Bash invocation.
# Receives: OAK_TOOL_CMD (the proposed command), OAK_AGENT_ID, OAK_PROBLEM_UUID

set -euo pipefail

CMD="${OAK_TOOL_CMD:-}"
AGENT="${OAK_AGENT_ID:-unknown}"

# Hard deny-list: commands that must never execute inside the harness.
DENY_PATTERNS=("rm -rf /" "DROP TABLE" "DROP DATABASE" "truncate /" \
               "chmod 777" "curl.*\|.*sh" "wget.*\|.*sh" ">/dev/sda")

for pattern in "${DENY_PATTERNS[@]}"; do
    if echo "$CMD" | grep -qi "$pattern"; then
        echo "[OAK-PROXY] BLOCKED by deny-list: $pattern" >&2
        # Log to Redis for telemetry
        redis-cli -u "${REDIS_URL}" LPUSH "oak:blocked:${AGENT}" \
            "{\"cmd\":\"${CMD}\",\"pattern\":\"${pattern}\",\"ts\":\"$(date -u +%s)\"}"
        exit 2  # Exit code 2 blocks the tool call in Claude Code
    fi
done

# Network egress restriction: only oak-net Docker network is reachable.
# Any attempt to reach external IPs is silently blocked by Docker network config.
# Log approved commands to Redis session history.
redis-cli -u "${REDIS_URL}" LPUSH "oak:session:${AGENT}:cmd_history" \
    "{\"cmd\":\"${CMD}\",\"ts\":\"$(date -u +%s)\"}" > /dev/null
redis-cli -u "${REDIS_URL}" LTRIM "oak:session:${AGENT}:cmd_history" 0 49

exit 0  # Allow
```

#### Redis Session State (session-state.py)

This script implements the "persistent state lite" that replaces OpenClaw's stateful terminal. At the start of each agent session, it restores the agent's last known context from Redis. At the end (via the `post-tool-use` hook), it updates the state. Agents no longer start from a cold blank context even after a container restart.

```python
# scripts/session-state.py
"""
Manages agent session state in Redis — mimics OpenClaw's persistent terminal
without any of its security exposure. State keys per agent:
  oak:session:{agent_id}:open_files  → sorted set (path, last_access_ts)
  oak:session:{agent_id}:cmd_history → list (last 50 commands as JSON)
  oak:session:{agent_id}:cwd         → string (current working directory)
  oak:session:{agent_id}:git_state   → hash (branch, staged, last_commit)
All keys expire after OAK_SESSION_TTL_HOURS (default: 24h).
"""
import sys, json, os, redis

r = redis.from_url(os.environ["REDIS_URL"])
agent_id = os.environ.get("OAK_AGENT_ID", "default")
ttl = int(os.environ.get("OAK_SESSION_TTL_HOURS", 24)) * 3600

def restore():
    """Print session context to stdout — Claude Code reads this as startup context."""
    state = {}
    cwd = r.get(f"oak:session:{agent_id}:cwd")
    if cwd:
        state["cwd"] = cwd.decode()
        os.chdir(state["cwd"])
    git = r.hgetall(f"oak:session:{agent_id}:git_state")
    if git:
        state["git"] = {k.decode(): v.decode() for k, v in git.items()}
    files = r.zrange(f"oak:session:{agent_id}:open_files", 0, 9, withscores=True)
    if files:
        state["recent_files"] = [f[0].decode() for f in files]
    history = r.lrange(f"oak:session:{agent_id}:cmd_history", 0, 9)
    if history:
        state["recent_commands"] = [json.loads(h) for h in history]
    if state:
        print(f"[OAK Session Restored] {json.dumps(state, indent=2)}")

def save(key, value):
    """Called by post-tool-use hook to update specific state keys."""
    full_key = f"oak:session:{agent_id}:{key}"
    r.set(full_key, value)
    r.expire(full_key, ttl)

if __name__ == "__main__":
    if sys.argv[1] == "restore":
        restore()
    elif sys.argv[1] == "save" and len(sys.argv) == 4:
        save(sys.argv[2], sys.argv[3])
```

#### oak-api-proxy (Dynamic Routing Layer)

The proxy is a small FastAPI application that sits between Claude Code and both Ollama and the Claude API. Claude Code is always configured with `ANTHROPIC_BASE_URL=http://oak-api-proxy:9000` — it never knows whether a given request went to Ollama or to Anthropic's cloud. The proxy decides per call.

```python
# oak_mcp/oak-api-proxy/main.py
"""
OAK API Proxy — dynamic routing between Ollama and Claude API.
Routing logic:
  1. Forward request to Ollama (default).
  2. Inspect response: if empty, starts with "I cannot", or confidence
     field below threshold → mark as "local stall".
  3. If ANTHROPIC_API_KEY is set and stall detected → retry via Claude API.
  4. Log every routing decision to Redis telemetry.
  5. Return whichever response was used to Claude Code transparently.
"""
import os, httpx, json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://oak-ollama:11434")
CLAUDE_URL  = "https://api.anthropic.com"
CLAUDE_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
STALL_PHRASES = ["i cannot", "i don't know how", "i'm unable", "as an ai"]

async def is_stalled(text: str) -> bool:
    """Detect low-quality local model responses that warrant API escalation."""
    t = text.lower().strip()
    return not t or any(t.startswith(p) for p in STALL_PHRASES)

@app.api_route("/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def proxy(path: str, request: Request):
    body = await request.body()
    headers = dict(request.headers)

    # Step 1: Try Ollama
    async with httpx.AsyncClient(timeout=120) as client:
        ollama_resp = await client.request(
            method=request.method,
            url=f"{OLLAMA_URL}/{path}",
            content=body,
            headers={k: v for k, v in headers.items() if k != "host"}
        )

    # Step 2: Check for stall and escalate if possible
    try:
        resp_json = ollama_resp.json()
        content = resp_json.get("content", [{}])[0].get("text", "")
        if await is_stalled(content) and CLAUDE_KEY:
            # Log escalation decision
            import redis; r = redis.from_url(os.environ.get("REDIS_URL","redis://oak-redis:6379"))
            r.incr("oak:telemetry:escalations")
            # Retry via Claude API with real key
            async with httpx.AsyncClient(timeout=120) as client:
                claude_resp = await client.request(
                    method=request.method,
                    url=f"{CLAUDE_URL}/{path}",
                    content=body,
                    headers={**headers, "x-api-key": CLAUDE_KEY,
                             "anthropic-version": "2023-06-01"}
                )
            return StreamingResponse(claude_resp.aiter_bytes(),
                                     status_code=claude_resp.status_code,
                                     media_type=claude_resp.headers.get("content-type"))
    except Exception:
        pass  # If parsing fails, return original Ollama response

    return StreamingResponse(
        iter([ollama_resp.content]),
        status_code=ollama_resp.status_code,
        media_type=ollama_resp.headers.get("content-type", "application/json")
    )
```

The proxy lives in `oak_mcp/oak-api-proxy/` and runs as its own Docker service (`oak-api-proxy`, port 9000). It is lightweight — a single Python file — and adds negligible latency since it is always on the same Docker network as Ollama.

#### Known Risks and Mitigations (Harness + Proxy Stack)

The harness/proxy combination is the highest-complexity part of OAK — many moving pieces where a silent bug can produce strange agent behaviour. The following risks are acknowledged and mitigated before agent swarms are enabled.

| Risk | Description | Mitigation |
|---|---|---|
| **Stall detection false positives** | Heuristics (`"I cannot"`, short length) may misclassify valid short Ollama responses as failures, triggering unnecessary Claude API escalation. | Stall detection is opt-in (`STALL_DETECTION_ENABLED=false` by default). When enabled, all escalation decisions are logged to Redis (`oak:telemetry:escalations`). Review telemetry before enabling in production. |
| **Stall detection false negatives** | A confidently wrong local response will not trigger escalation. | Treat local-only mode as the production baseline. Escalation is a quality improvement, not a correctness guarantee. The Judge Agent catches bad outputs regardless of which model produced them. |
| **Dual deny-list drift** | `tool-proxy.sh` (layer 1) and `pre-tool-use.sh` (layer 2) can diverge if one is updated and the other is not. | Both scripts import shared deny patterns from a single source file (`scripts/deny-patterns.txt`). Any pattern change must update this file; hooks and proxy read from it at runtime. |
| **Redis session state inconsistency** | Concurrent or crashed sessions can leave stale or partial state keys, misleading agents on restore. | All session keys carry TTL (default 24h). A health-check endpoint (`GET /api/agents/session/{id}/health`) validates key completeness and purges stale sessions. |
| **Container proliferation** | Without caps, long-running or stalled harness containers can exhaust host memory. | `MAX_HARNESS_CONTAINERS` is enforced by the TRUNK before launching new containers. `docker stats` is exposed via the telemetry API. |

**Testing requirements before enabling agent swarms.** The harness and proxy must have passing unit tests for: `tool-proxy.sh` pattern matching (allowed and denied commands); `session-state.py` round-trip state, TTL, and concurrent-session behaviour; `oak-api-proxy` Ollama happy path, stall trigger, and missing-key fallback. These tests must pass in CI before Phase 2 begins.

---

## 5. Docker Infrastructure

### 5.1 Base Compose (docker-compose.base.yml)

All platform-specific compose files extend this base. Services defined here: `oak-postgres`, `oak-redis`, `oak-ollama`, `oak-api-proxy` (new), `oak-harness` (new), `oak-api`, `oak-ui`.

```yaml
# docker-compose.base.yml
version: "3.9"

x-oak-common: &oak-common
  restart: unless-stopped
  networks:
    - oak-net
  env_file:
    - .env

services:
  oak-postgres:
    <<: *oak-common
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: oak
      POSTGRES_PASSWORD: oak
      POSTGRES_DB: oak
    volumes:
      - oak-pgdata:/var/lib/postgresql/data
      - ./api/db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "5432:5432"

  oak-redis:
    <<: *oak-common
    image: redis:7-alpine
    volumes:
      - oak-redisdata:/data
    ports:
      - "6379:6379"

  oak-ollama:
    <<: *oak-common
    image: ollama/ollama:latest
    volumes:
      - oak-ollamadata:/root/.ollama
    ports:
      - "11434:11434"
    # Ollama exposes Anthropic-compatible /v1/ endpoint natively.
    # Claude Code reaches it via oak-api-proxy, not directly.

  # ── NEW: Dynamic API routing proxy ────────────────────────────────────────
  # Sits between Claude Code (in oak-harness) and both Ollama + Claude API.
  # Routes each call to local Ollama by default; escalates to Claude API on stall.
  oak-api-proxy:
    <<: *oak-common
    build:
      context: ./oak_mcp/oak-api-proxy
      dockerfile: Dockerfile
    ports:
      - "9000:9000"
    environment:
      OLLAMA_BASE_URL: http://oak-ollama:11434
      REDIS_URL: redis://oak-redis:6379
      # ANTHROPIC_API_KEY is read from .env — empty by default (local-only mode)
    depends_on:
      - oak-ollama
      - oak-redis

  # ── NEW: Claude Code harness container ────────────────────────────────────
  # Each agent session runs as an instance of this image.
  # Bundles: Claude Code binary + tool-proxy + Redis session state.
  # All API calls route through oak-api-proxy.
  # All filesystem access is sandboxed to /workspace.
  oak-harness:
    <<: *oak-common
    build:
      context: ./docker/claude-harness
      dockerfile: Dockerfile
    environment:
      ANTHROPIC_BASE_URL: http://oak-api-proxy:9000   # The canonical Ollama recipe
      ANTHROPIC_AUTH_TOKEN: ollama                     # Required for Ollama compat
      ANTHROPIC_API_KEY: ""                            # Explicitly empty; proxy manages
      REDIS_URL: redis://oak-redis:6379
      DATABASE_URL: postgresql://oak:oak@oak-postgres:5432/oak
      CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"
    volumes:
      - ~/oak-workspaces:/workspace                   # Worktrees accessible in sandbox
      - /mnt/oak-data:/mnt/oak-data                   # Raw problem data (read-only mount)
      - ~/.claude:/root/.claude                        # Claude Code config, agents, hooks
    depends_on:
      - oak-api-proxy
      - oak-postgres
      - oak-redis
    # Not started automatically — launched per problem by new-problem.sh
    profiles: ["harness"]

  oak-api:
    <<: *oak-common
    build: ./api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://oak:oak@oak-postgres:5432/oak
      REDIS_URL: redis://oak-redis:6379
      OLLAMA_BASE_URL: http://oak-ollama:11434
    depends_on:
      - oak-postgres
      - oak-redis
      - oak-ollama

  oak-ui:
    <<: *oak-common
    build: ./ui
    ports:
      - "8501:8501"
    environment:
      OAK_API_URL: http://oak-api:8000
    depends_on:
      - oak-api

volumes:
  oak-pgdata:
  oak-redisdata:
  oak-ollamadata:

networks:
  oak-net:
    driver: bridge
    # Only services on oak-net can communicate. The harness container has no
    # external network access — Docker enforces egress restriction by design.
```

### 5.2 DGX Spark Profile (docker-compose.dgx.yml)

```yaml
# docker-compose.dgx.yml — extends base with DGX GPU config
include:
  - docker-compose.base.yml

services:
  oak-ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      OAK_MODE: dgx
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility

  oak-api:
    environment:
      OAK_MODE: dgx
      # DGX has full memory — enable 70B models by default
      DEFAULT_MODEL: llama3.3:70b
      CODER_MODEL: qwen2.5-coder:32b
      ANALYSIS_MODEL: llama3.3:70b
```

### 5.3 Mac Mini Profile (docker-compose.mini.yml)

The mini profile uses SQLite as the persistence backend for the skill index (PostgreSQL still runs for problem data, but smaller footprint settings apply), and constrains model choices to those that run at acceptable speed on M4 Pro 64GB via Ollama's Metal backend.

```yaml
# docker-compose.mini.yml
include:
  - docker-compose.base.yml

services:
  oak-api:
    environment:
      OAK_MODE: mini
      DEFAULT_MODEL: llama3.2:3b      # Fast on M4
      CODER_MODEL: qwen2.5-coder:7b
      ANALYSIS_MODEL: llama3.2:8b
      # Escalate more aggressively to Claude API on mini
      LOCAL_CONFIDENCE_THRESHOLD: "0.7"
```

### 5.4 Environment File (.env template)

```bash
OAK_MODE=dgx                          # dgx | mini | cloud

# ── Ollama + Claude Code canonical recipe (harness.md) ─────────────────────
# These three variables together tell Claude Code to use Ollama locally.
# ANTHROPIC_BASE_URL points to the oak-api-proxy, not directly to Ollama,
# so the proxy can dynamically escalate to Claude API on stall detection.
ANTHROPIC_BASE_URL=http://oak-api-proxy:9000
ANTHROPIC_AUTH_TOKEN=ollama           # Required — Ollama expects this
ANTHROPIC_API_KEY=                    # Intentionally empty; proxy holds real key

# ── Optional Claude API escalation ─────────────────────────────────────────
# Set this to enable the proxy's escalation tier. Leave empty for fully local.
ANTHROPIC_API_KEY_REAL=               # The real Anthropic key (proxy reads this)

PROBLEM_UUID=                          # Set per problem by new-problem.sh
OAK_SKILL_PROMO_THRESHOLD=2            # Problems before probationary → permanent
OAK_MEMORY_TTL_DAYS=90                 # Episodic memory before cold archive
OAK_IDLE_TIMEOUT_SECONDS=120           # Teammate-idle hook threshold
OAK_SESSION_TTL_HOURS=24               # Redis session state expiry

# ── Resource caps (tuning knobs, not architectural limits) ──────────────────────────────
# Orchestrator enforces MAX_AGENTS_PER_PROBLEM by refusing to spawn beyond it.
# TRUNK enforces MAX_CONCURRENT_PROBLEMS by returning 429 on the 4th active problem.
# Docker enforces MAX_HARNESS_CONTAINERS via container count check in new-problem.sh.
MAX_AGENTS_PER_PROBLEM=10              # Soft cap per problem (dgx: 10, mini: 4)
MAX_CONCURRENT_PROBLEMS=3             # Hard cap on active problems at once
MAX_HARNESS_CONTAINERS=20             # Total harness containers across all problems

# ── Proxy behaviour ──────────────────────────────────────────────────────────────
STALL_DETECTION_ENABLED=false          # Opt-in: enable heuristic escalation
LOCAL_CONFIDENCE_THRESHOLD=0.8        # (mini only) escalate more aggressively
```

---

## 6. PostgreSQL Schema (Full DDL)

```sql
-- schema.sql: Run once on first postgres startup

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Problems ────────────────────────────────────────────────────────────────
CREATE TABLE problems (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title         TEXT NOT NULL,
  description   TEXT,
  status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','assembling','active','complete','failed')),
  data_manifest JSONB,          -- list of ingested file paths / table names
  solution_url  TEXT,           -- Streamlit spoke URL when complete
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at  TIMESTAMPTZ
);

-- ─── Tasks (Shared Task List) ─────────────────────────────────────────────────
CREATE TABLE tasks (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  problem_id    UUID REFERENCES problems(id) ON DELETE CASCADE,
  type          TEXT NOT NULL   -- ingest | analyse | model | synthesise | validate
                  CHECK (type IN ('ingest','analyse','model','synthesise','validate')),
  title         TEXT NOT NULL,
  description   TEXT,
  status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','claimed','complete','failed')),
  assigned_to   TEXT,           -- agent name
  depends_on    UUID[],         -- task IDs that must be complete first
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  claimed_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ
);

-- ─── Mailbox (peer-to-peer agent messages) ────────────────────────────────────
CREATE TABLE mailbox (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  problem_id    UUID REFERENCES problems(id) ON DELETE CASCADE,
  from_agent    TEXT NOT NULL,
  to_agent      TEXT,           -- NULL = broadcast
  subject       TEXT,
  body          TEXT NOT NULL,
  read          BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Episodic Memory ─────────────────────────────────────────────────────────
CREATE TABLE episodes (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  problem_id    UUID REFERENCES problems(id),
  agent_id      TEXT NOT NULL,
  event_type    TEXT NOT NULL,  -- observation | decision | error | outcome
  content       TEXT NOT NULL,
  importance    FLOAT NOT NULL DEFAULT 0.5,  -- 0-1 score
  embedding     vector(1536),   -- pgvector embedding of content
  retrieved_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON episodes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON episodes (agent_id, importance DESC);

-- ─── Skill Library Index ──────────────────────────────────────────────────────
CREATE TABLE skills (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT UNIQUE NOT NULL,
  category      TEXT NOT NULL,  -- etl | analysis | ml | ui | infra
  keywords      TEXT[],
  file_path     TEXT NOT NULL,  -- path to SKILL.md on filesystem
  status        TEXT NOT NULL DEFAULT 'probationary'
                  CHECK (status IN ('probationary','permanent','deprecated')),
  problem_uses  UUID[],         -- problem IDs where this skill was applied
  use_count     INT NOT NULL DEFAULT 0,
  last_used_at  TIMESTAMPTZ,
  embedding     vector(1536),   -- pgvector embedding of skill description
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON skills USING hnsw (embedding vector_cosine_ops);

-- ─── Agent Telemetry ──────────────────────────────────────────────────────────
CREATE TABLE agent_telemetry (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  problem_id    UUID REFERENCES problems(id),
  agent_id      TEXT NOT NULL,
  tool_name     TEXT NOT NULL,
  duration_ms   INT,
  success       BOOLEAN NOT NULL DEFAULT TRUE,
  error_msg     TEXT,
  model_used    TEXT,
  tokens_in     INT,
  tokens_out    INT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Judge Verdicts ───────────────────────────────────────────────────────────
CREATE TABLE judge_verdicts (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_id       UUID REFERENCES tasks(id),
  verdict       TEXT NOT NULL CHECK (verdict IN ('pass','fail')),
  checks        JSONB,          -- { lint: true, schema: true, smoke: false, ... }
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 7. Inference Tiering Policy

Claude Code's Anthropic SDK calls are routed through the `oak-api-proxy` container, which forwards them to Ollama's Anthropic-compatible `/v1/` endpoint by default. This is the concrete implementation of the Ollama + Claude Code integration: `ANTHROPIC_BASE_URL` points to the proxy, `ANTHROPIC_AUTH_TOKEN=ollama` satisfies Ollama's auth expectation, and `ANTHROPIC_API_KEY` is left empty in the harness (the proxy holds the real key and uses it only on escalation).

**Default routing strategy: `PassthroughStrategy`.** The proxy is controlled by the `ROUTING_STRATEGY` configuration value. The default — and the correct v1 production setting — is `ROUTING_STRATEGY=passthrough`. In this mode every call goes to Ollama unconditionally; no escalation logic is active regardless of response content. There is no code path through which a stall condition can trigger escalation unless `STALL_DETECTION_ENABLED=true` is explicitly set in `.env`. This is the "no accidental cleverness" guarantee: cloud escalation is opt-in per operator decision, not triggered by a heuristic firing in production when the operator did not intend it. The routing strategy is defined as a `RoutingStrategy` enum in `api/config.py` (see PRD §2.2); changing it requires only a `.env` edit and a proxy restart — no code change.

The primary coding model is `qwen3-coder`, named explicitly in the Ollama integration documentation as excelling at code-heavy agent tasks. `glm-4.7` is an effective alternative for analytical workloads. Heavier reasoning still uses `llama3.3:70b`.

| Task class | Default model (Ollama) | Escalation trigger | Claude API model |
|---|---|---|---|
| ETL scripting, DDL, boilerplate | `qwen3-coder` | Never | — |
| Statistical analysis, EDA | `glm-4.7` | Novel domain flag | `claude-haiku-4-5` |
| Standard ML setup | `deepseek-v3` | Never | — |
| Cross-domain synthesis | `llama3.3:70b` | Local stall detected by proxy | `claude-sonnet-4-5` |
| Solution architecture | `llama3.3:70b` | Always (high-consequence; proxy forces escalation) | `claude-sonnet-4-5` |
| Judge validation | `qwen3-coder` | Never | — |
| Meta-agent prompt rewrite | `glm-4.7` | Always | `claude-haiku-4-5` |
| Emergency re-try | `llama3.3:70b` | After 2 Sonnet failures | `claude-opus-4-5` |

The proxy detects "local stall" via three signals: an empty completion, a response opening with known failure phrases (`"I cannot"`, `"I'm unable"`, `"As an AI"`), or a response shorter than 20 tokens for a task that clearly warrants more. Any of these triggers a transparent retry via the Claude API without the agent being aware the routing changed. If `ANTHROPIC_API_KEY` is absent, the system logs the escalation failure, retries locally with an adjusted prompt, and continues.

---

## 8. FastAPI Surface

The API lives in `api/main.py` and is the sole interface between the CANOPY UI and the GROVE agent engine. Every endpoint returns JSON; errors follow RFC 7807 Problem Details.

```python
# api/main.py (abbreviated)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import problems, agents, tasks, skills, telemetry
from api.ws.stream import router as ws_router

app = FastAPI(title="OAK API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])

app.include_router(problems.router, prefix="/api/problems")
app.include_router(agents.router,   prefix="/api/agents")
app.include_router(tasks.router,    prefix="/api/tasks")
app.include_router(skills.router,   prefix="/api/skills")
app.include_router(telemetry.router,prefix="/api/telemetry")
app.include_router(ws_router)
```

**Key endpoints:**

`POST /api/problems` — Accept problem description + data file upload. Creates a UUID, writes to `problems` table, copies data to `/mnt/oak-data/{uuid}/`, calls `new-problem.sh` to create a git worktree, and triggers the Orchestrator agent as a subprocess. Returns `{problem_id, status: "assembling"}`.

`GET /api/problems/{id}` — Returns full problem record including `solution_url` when available.

`GET /api/agents/status` — Returns current agent session list with status (idle / active / blocked) and current task.

`GET /api/tasks?problem_id={id}` — Returns the full task list for a problem with status and assignee.

`GET /api/skills?query={text}&category={cat}` — Semantic search over the skill library using pgvector cosine similarity. Returns top-5 matching skills with relevance scores.

`GET /api/telemetry?problem_id={id}` — Returns aggregated telemetry for a problem: tokens per agent, duration per task, error counts.

`WS /ws/stream/{problem_id}` — WebSocket endpoint. The agent engine publishes events to a Redis pub/sub channel `oak:stream:{problem_id}`; this endpoint subscribes and forwards to the browser. Event types: `agent_spawned`, `task_claimed`, `mailbox_message`, `judge_verdict`, `solution_ready`.

---

## 9. UI Canopy (Streamlit Hub)

The Hub is a Streamlit multi-page application at `~/oak-workspaces/ui/`. It is the human's window into OAK. It self-evolves: when the Software Architect agent solves a new problem class, it generates new Streamlit pages and opens a PR against `oak/ui`. The human merges the PR; Streamlit Cloud redeploys automatically.

### 9.1 Pages

`canopy.py` (main) — Dashboard: active problems, recent completions, skill library summary, system health.

`pages/01_new_problem.py` — Problem submission: text description field, file upload (CSV/JSON/TXT), optional DB connection string. Calls `POST /api/problems` and redirects to the problem status page.

`pages/02_problem_status.py` — Live view of an active problem. Connects to `WS /ws/stream/{problem_id}` and renders agent events as a real-time activity feed. Shows task board (Kanban columns: pending / claimed / complete). Shows Judge verdicts as they arrive.

`pages/03_solution_gallery.py` — Grid of all completed problems with title, date, and link to the deployed solution spoke. Solutions are Streamlit apps deployed to Streamlit Cloud from the problem branch.

`pages/04_skill_library.py` — Searchable catalog of all permanent and probationary skills. Shows use count, last used, and a link to the SKILL.md file.

`pages/05_telemetry.py` — Aggregated metrics: tokens per agent, problem throughput, model usage breakdown, error rates, skill library growth over time.

### 9.2 Solution Spokes

Each problem produces a standalone Streamlit or Dash application committed to `oak/problem-{uuid}` branch. This is the deployed solution the user actually works with. The spoke is self-contained: it includes its own data loading, visualisations, and any interactive controls specific to that problem. The Software Architect agent generates spoke code; the Judge Agent validates it; once merged and deployed, the Hub's solution gallery links to it.

---

## 10. Problem Lifecycle (End-to-End)

This section traces a single problem from submission to deployed solution.

**Step 1 — Arrival.** User submits via Hub. `POST /api/problems` creates a UUID (`p-abc123`), copies uploaded files to `/mnt/oak-data/p-abc123/`, writes the problem record, and calls `scripts/new-problem.sh p-abc123`. That script runs: `git worktree add ~/oak-workspaces/problem-p-abc123 -b oak/problem-p-abc123` and writes a `PROBLEM.md` manifest to the new worktree. The WebSocket stream channel `oak:stream:p-abc123` is opened. Status → `assembling`.

**Step 2 — Assembly.** The Orchestrator agent session starts. It reads `PROBLEM.md`, queries the oak-skills MCP for relevant prior skills, and decomposes the problem into typed tasks. Tasks are written to the `tasks` table with dependency edges. Example decomposition for a time-series CSV problem: `ingest:profile-csv` → `analyse:eda-timeseries` → `model:anomaly-detection` → `synthesise:dashboard` → `validate:judge`. The Orchestrator broadcasts task availability to the Redis mailbox and publishes `agent_spawned` events to the stream.

**Step 3 — Data ingestion.** The Data Engineer agent claims the `ingest` task. It reads from `/mnt/oak-data/p-abc123/`, profiles every column using pandas, infers DDL, and creates tables in PostgreSQL via the postgres MCP. It applies the `etl-csv-ingestion` skill if present in the permanent library, otherwise derives the approach and flags it for skill extraction. Completion publishes `task_claimed → task_complete` events.

**Step 4 — Analysis.** The Data Scientist agent claims `analyse`. It runs statistical analysis against the new PostgreSQL tables, generates pgvector embeddings of text columns via the oak-memory MCP, and writes an `analysis_report.md` to the problem worktree. It messages the ML Engineer via the mailbox with key findings.

**Step 5 — Modelling.** The ML Engineer reads the analysis report and mailbox message. It queries the oak-skills MCP: "time-series anomaly detection". If a permanent skill exists, it applies it; otherwise it selects an approach (Isolation Forest, LSTM autoencoder, etc.), writes the model code, and generates an inference wrapper. It writes `model/` to the problem worktree.

**Step 6 — Synthesis.** The Software Architect reads all worktree artefacts and generates `app.py` — the solution spoke. This is a self-contained Streamlit app with data loading, model inference, and visualisations tailored to this specific problem. The Architect also checks: does this problem class require a new Hub page? If yes, it generates `pages/06_timeseries_explorer.py` and opens a PR against `oak/ui`.

**Step 7 — Validation.** The Judge Agent runs: `ruff check app.py`, `mypy app.py`, and a smoke test (imports, data load, render without crash). If all pass, it inserts a PASS verdict into `judge_verdicts` and publishes `judge_verdict: pass` to the stream. The `task-completed.sh` hook unblocks the validate task closure.

**Step 8 — Delivery.** The Orchestrator marks the problem `complete`. The API updates `solution_url` in the problems table. The Hub's solution gallery gains a new entry. The Skill Extractor runs asynchronously, inspecting the worktree for promotable patterns.

**Step 9 — Learning.** The Skill Extractor writes candidate skills to `skills/probationary/`. If the same skill pattern has been seen twice before, it is promoted to `skills/permanent/` and indexed in PostgreSQL. The `tasks`, `episodes`, and `agent_telemetry` records persist for future meta-agent analysis. The problem worktree is retained for 30 days then archived (branch preserved in git history).

---

## 11. Self-Evolution Loop

OAK's intelligence compounds across problems via three mechanisms.

**Skill compounding.** Every problem that adds a new permanent skill makes all subsequent problems of that class faster. The first time OAK encounters a gas turbine vibration dataset, it reasons from first principles. The second time, it retrieves the `rotating-equipment-anomaly` skill and composes rather than derives. By the tenth similar problem, the agent grove executes the pattern in a fraction of the original time.

**UI evolution.** When the Software Architect opens a PR for a new Hub page (e.g., `pages/06_timeseries_explorer.py`), the operator reviews and merges. GitHub Actions triggers a Streamlit Cloud redeploy. The Hub now surfaces a new entry point for time-series problems. Future users submitting similar problems find a pre-built analysis template waiting for them.

**Prompt evolution.** The Meta Agent (running daily or after every 10 problems) reads the `agent_telemetry` table and identifies patterns: if the Data Engineer agent fails to handle semicolon-delimited files 80% of the time, the Meta Agent generates a proposed CLAUDE.md amendment for the `data-engineer` subagent and opens a PR against `oak/agents`. The operator reviews and merges; from that point forward every Data Engineer agent instance has the improvement built into its context.

---

## 12. Hardware Journey

The `OAK_MODE` environment variable and the corresponding compose file control all platform differences. No application code changes are required to switch platforms.

| Platform | Compose file | Default models | Notes |
|---|---|---|---|
| DGX Spark (init) | `docker-compose.dgx.yml` | Llama-3.3-70B, Qwen2.5-Coder-32B | Full NVIDIA GPU passthrough; 128GB unified; concurrent problems |
| Mac Mini M4 Pro (port) | `docker-compose.mini.yml` | Llama-3.2-8B, Qwen2.5-Coder-7B | Metal backend via Ollama; single problem at a time; faster Claude API escalation |
| Cloud multi-GPU (scale) | `docker-compose.cloud.yml` | Llama-3.3-70B (multi-GPU) | RunPod / DigitalOcean A100 cluster; Kubernetes overlay for concurrent problems |

The cloud compose extends the base with GPU node selectors and scales `oak-ollama` horizontally via vLLM rather than Ollama for higher throughput on concurrent requests.

---

## 13. Bootstrap Sequence (Claude Code Entry Point)

These are the exact commands a Claude Code session should execute to initialise OAK on a fresh DGX Spark node. Save this as `scripts/bootstrap.sh` and run it as the first action. The sequence installs infrastructure, builds the two new harness-related Docker images, pulls local models including qwen3-coder, and verifies the full routing chain from Claude Code → proxy → Ollama before any agent work begins.

```bash
#!/bin/bash
set -euo pipefail

echo "=== OAK Bootstrap v1.1: DGX Spark ==="

# 1. Clone repository
git clone https://github.com/SharathSPhD/oak.git ~/oak
cd ~/oak

# 2. Create branch structure
git checkout -b oak/agents  && git push -u origin oak/agents
git checkout -b oak/skills  && git push -u origin oak/skills
git checkout -b oak/ui      && git push -u origin oak/ui
git checkout main

# 3. Create workspace directory and worktrees
mkdir -p ~/oak-workspaces
git worktree add ~/oak-workspaces/agents oak/agents
git worktree add ~/oak-workspaces/skills oak/skills
git worktree add ~/oak-workspaces/ui     oak/ui

# 4. Create skill library directories
mkdir -p ~/oak-workspaces/skills/{permanent,probationary}
touch ~/oak-workspaces/skills/permanent/.gitkeep
touch ~/oak-workspaces/skills/probationary/.gitkeep

# 5. Configure environment
cp .env.template .env
# The three critical Ollama + Claude Code variables are pre-set in .env.template:
#   ANTHROPIC_BASE_URL=http://oak-api-proxy:9000  (proxy, not Ollama directly)
#   ANTHROPIC_AUTH_TOKEN=ollama
#   ANTHROPIC_API_KEY=                            (empty; proxy manages escalation)
echo "Review .env — optionally set ANTHROPIC_API_KEY to enable Claude API escalation."
echo "Leave it empty to run fully local. Press enter to continue."
read -r

# 6. Build the two harness-related images BEFORE starting the stack.
# These must be built first so docker compose up finds them.
echo "--- Building oak-api-proxy (dynamic routing layer) ---"
docker build -t oak/api-proxy:latest ./oak_mcp/oak-api-proxy/

echo "--- Building oak-harness (Claude Code sandbox container) ---"
docker build -t oak/harness:latest ./docker/claude-harness/

# 7. Start the core Docker stack (DGX profile)
docker compose -f docker/docker-compose.dgx.yml up -d \
    oak-postgres oak-redis oak-ollama oak-api-proxy oak-api oak-ui
sleep 15  # Wait for postgres to be ready

# 8. Verify database schema (schema.sql auto-runs via initdb)
docker exec oak-postgres psql -U oak -d oak -c "\dt" | grep -c "oak" && \
    echo "✓ Schema verified" || echo "✗ Schema check failed — re-run schema.sql manually"

# 9. Pull local models — qwen3-coder is the primary (recommended by Ollama docs
#    for code-heavy Claude Code agent tasks); others cover reasoning and analysis.
echo "--- Pulling Ollama models (this will take several minutes on first run) ---"
docker exec oak-ollama ollama pull qwen3-coder         # Primary: all coding tasks
docker exec oak-ollama ollama pull glm-4.7              # Analysis and EDA tasks
docker exec oak-ollama ollama pull llama3.3:70b         # Heavy reasoning, synthesis
docker exec oak-ollama ollama pull deepseek-v3          # ML task scripting

# 10. Verify the full routing chain:
#     Claude Code → oak-api-proxy (port 9000) → Ollama /v1/models
echo "--- Verifying proxy routing chain ---"
curl -s -H "Authorization: Bearer ollama" \
    http://localhost:9000/v1/models | \
    python3 -c "import sys,json; d=json.load(sys.stdin); \
    print('✓ Proxy OK. Models:', [m['id'] for m in d.get('data',[])])"

# Also verify direct Ollama access (bypassing proxy) for diagnostics
curl -s http://localhost:11434/api/tags | \
    python3 -c "import sys,json; d=json.load(sys.stdin); \
    print('✓ Ollama OK. Models:', [m['name'] for m in d.get('models',[])])"

# 11. Enable Claude Code agent teams (set globally, also inside harness container env)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
echo "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" >> ~/.bashrc

# 12. Install MCP server dependencies
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-postgres
pip install mcp-server-git --break-system-packages

# 13. Install and verify custom OAK MCP servers
cd ~/oak/oak_mcp/oak-memory-mcp && pip install -e . --break-system-packages
cd ~/oak/oak_mcp/oak-skills-mcp && pip install -e . --break-system-packages
cd ~/oak

# 14. Launch UI Hub
docker compose -f docker/docker-compose.dgx.yml exec oak-ui \
    streamlit run canopy.py --server.port 8501 --server.headless true &

echo ""
echo "=== OAK Bootstrap v1.1 Complete ==="
echo "Hub:         http://localhost:8501"
echo "API:         http://localhost:8000/docs"
echo "API Proxy:   http://localhost:9000  (Claude Code → this → Ollama/Claude API)"
echo "Ollama:      http://localhost:11434"
echo ""
echo "To start a new problem:    scripts/new-problem.sh"
echo "To launch a harness agent: docker run --rm --network oak_oak-net \\"
echo "    -e OAK_AGENT_ID=orchestrator -e PROBLEM_UUID=\$PROBLEM_UUID \\"
echo "    -v ~/oak-workspaces:/workspace oak/harness:latest"
```

**new-problem.sh** — creates an isolated worktree and launches the orchestrator agent inside an `oak-harness` container:

```bash
#!/bin/bash
PROBLEM_UUID=${1:-$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -c1-8)}
BRANCH="oak/problem-${PROBLEM_UUID}"
WORKSPACE="${HOME}/oak-workspaces/problem-${PROBLEM_UUID}"

cd ~/oak
git worktree add ${WORKSPACE} -b ${BRANCH}
git push -u origin ${BRANCH}

# Write problem manifest stub
cat > ${WORKSPACE}/PROBLEM.md << EOF
# Problem: ${PROBLEM_UUID}
## Status: pending
## Data location: /mnt/oak-data/${PROBLEM_UUID}/
## Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Description
[Agent will populate after reading problem submission]

## Data manifest
[Agent will populate after ingestion]
EOF

export PROBLEM_UUID=${PROBLEM_UUID}
echo "Problem workspace ready: ${WORKSPACE}"
echo "Branch: ${BRANCH}"
echo ""
echo "Launching orchestrator agent in oak-harness container..."
# The harness container receives the three Ollama env vars from the image ENV
# directives plus problem-specific vars below. It starts claude --model qwen3-coder
# pointed at the api-proxy, which routes to Ollama by default.
docker run --rm \
    --network oak_oak-net \
    --name "oak-agent-${PROBLEM_UUID}-orchestrator" \
    -e OAK_AGENT_ID="orchestrator" \
    -e OAK_PROBLEM_UUID="${PROBLEM_UUID}" \
    -e REDIS_URL="redis://oak-redis:6379" \
    -e DATABASE_URL="postgresql://oak:oak@oak-postgres:5432/oak" \
    -v ${HOME}/oak-workspaces:/workspace \
    -v /mnt/oak-data:/mnt/oak-data:ro \
    -v ${HOME}/.claude:/root/.claude \
    oak/harness:latest
```

---

## 14. Phased Implementation Roadmap

Each phase must reach its exit criteria before the next phase begins. Exit criteria are SLO-style: they specify observable, testable conditions, not feature presence. A phase is not complete because the feature exists — it is complete because the feature is correct, tested, and observable.

### Phase 0 — Walking Skeleton (Weeks 1–2, DGX Spark)

**Goal:** Data flows from file to database to API with zero agent involvement. The purpose is to lock in correct data lifecycle, schema constraints, and API contract before any agent complexity is added.

**Scope:** Bring up `oak-postgres`, `oak-redis`, `oak-ollama`, and `oak-api` only. Implement `POST /api/problems` and a single non-agent ingestion script that reads a CSV from `/mnt/oak-data/{uuid}/`, loads it into PostgreSQL, and generates a trivial static Streamlit `app.py`. No Claude Code, no harness, no agent teams.

**Tests to write:**
- Unit tests for all five API routers and DDL constraints (foreign keys, CHECK constraints, NOT NULL).
- Integration test: "1 CSV in → one PostgreSQL table + `app.py` out" passes in CI with no agent involvement.

**Exit criteria (all must pass):**
- `docker compose up` with `oak-postgres`, `oak-redis`, `oak-ollama`, `oak-api` succeeds; all four services report healthy.
- `curl http://localhost:11434/v1/models` returns at least one local model.
- `psql` shows all eight schema tables with correct column definitions.
- `POST /api/problems` with a sample CSV creates all expected records; `GET /api/problems/{id}` returns them correctly.
- CI integration test passes: 1 CSV in → table in postgres + valid `app.py` out.
- No agent complexity is present in this phase — `scripts/bootstrap.sh` is the only orchestration.

### Phase 1 — Hardened Harness + Single Agent (Weeks 3–4)

**Goal:** The `oak-harness` container and `oak-api-proxy` are production-quality and fully test-covered *before* any agent teamwork is enabled. Introducing teams on a fragile harness is the highest-risk failure mode in the system.

**Scope:** Build and test `oak-harness` and `oak-api-proxy`. Run a *single* Claude Code agent (no teams, no subagents) inside the harness performing the same CSV-to-app task as Phase 0. Stall detection remains disabled (`STALL_DETECTION_ENABLED=false`).

**Tests to write:**
- `tool-proxy.sh`: unit tests for every deny pattern (verify blocked commands exit 2; verify allowed commands exit 0 and are logged to Redis).
- `session-state.py`: round-trip state (save → container restart → restore), TTL expiry, concurrent-session isolation.
- `oak-api-proxy`: Ollama happy path, Ollama timeout/error handling, missing-key fallback (no crash, logs failure, returns best Ollama response).

**Exit criteria (all must pass):**
- All harness and proxy unit tests pass in CI.
- Single agent inside harness completes CSV-to-app task end-to-end with no errors.
- Tool proxy correctly blocks at least three canonical denied commands in tests.
- Redis session state survives a simulated container restart (`docker stop` → `docker start`).
- `GET /api/agents/status` shows the running agent session accurately.

### Phase 2 — Agent Teams + Task List + Mailbox (Weeks 5–6)

**Goal:** Multi-agent coordination is proven correct on simple canonical problem types before skill learning or UI evolution is layered on.

**Scope:** Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Wire up Orchestrator, Data Engineer, Data Scientist, and Judge Agents using `tasks` and `mailbox` tables. Keep solutions extremely simple (one or two basic Streamlit plots). No skill extraction, no UI PRs.

**Tests to write:**
- Task state machine: valid transitions only (`pending → claimed → complete`; illegal direct `pending → complete` is rejected).
- Mailbox: message delivery, `read` flag toggle, broadcast (NULL `to_agent`) vs directed delivery.
- Judge gating: `task-completed.sh` hook blocks closure when no PASS verdict exists; unblocks when PASS is present.

**Exit criteria (all must pass):**
- Two canonical problem types (e.g., CSV summary + time-series plot) complete end-to-end with Orchestrator + three specialists.
- Task board in `GET /api/tasks?problem_id={id}` reflects accurate real-time status.
- Mailbox messages are exchanged and readable in PostgreSQL with correct `read` flags.
- A problem with a Judge FAIL verdict causes the relevant agent to be re-tasked (observable in task log).
- Failure of one agent (simulated) is visible as a blocked task, not a silent hang.
- Fewer than 2 unexpected failures per 10 test runs at this phase.

### Phase 3 — Memory, Skill Library, and Hub (Weeks 7–8)

**Goal:** OAK learns from its own work. Skill reuse is measurable. The Hub is live. UI evolution is constrained to analytics tab additions only until proven stable.

**Scope:** Implement `oak-memory-mcp`, `oak-skills-mcp`, Skill Extractor, probationary promotion logic. Deploy Streamlit Hub to Streamlit Cloud on `oak/ui` branch with WebSocket stream. Implement constrained UI evolution: Software Architect may add analytics tabs to existing pages only — no entirely new pages yet.

**Tests to write:**
- Skill promotion: verify that a skill extracted from Problem 1 appears in `probationary/`, is retrieved via pgvector on Problem 2, and is promoted to `permanent/` after Problem 3.
- pgvector: semantic search returns correct skill with top-1 accuracy on known queries.
- WebSocket stream: all expected event types (`agent_spawned`, `task_claimed`, `judge_verdict`, `solution_ready`) are emitted and received by the Hub.
- UI PR: Software Architect PR contains valid Python, passes `ruff` and `mypy` in CI, and does not break existing Hub navigation.

**Exit criteria (all must pass):**
- Hub is accessible at a public Streamlit Cloud URL.
- A skill extracted from Problem 1 (ETL type) is retrievable via `GET /api/skills?query=...` and reused by the agent on Problem 2 of the same type.
- Median time-to-app for Problem 3 (same type as 1 and 2) is measurably lower than Problem 1 via `agent_telemetry` (target: any reduction; 50% reduction is the Section 1.1 long-run target).
- After merging a Software Architect PR, Hub redeploys within 5 minutes with the new tab visible and existing pages unbroken.
- pgvector semantic search latency under 200ms for skill queries at the current library size.

### Phase 4 — Mac Mini Port and Stall Detection (Weeks 9–10)

**Goal:** Full platform portability is verified. Stall-based Claude API escalation is enabled and calibrated with observed telemetry.

**Scope:** Switch to `docker-compose.mini.yml` on Mac Mini M4 Pro 64GB. Verify Metal backend, smaller model defaults, and aggressive escalation threshold. Enable `STALL_DETECTION_ENABLED=true` only after reviewing Phase 3 proxy telemetry to calibrate thresholds. Expand UI evolution to allow full new pages (not just tabs).

**Exit criteria (all must pass):**
- Full problem lifecycle (ingest → analyse → synthesise → validate → deploy) completes on Mac Mini.
- `oak-ollama` logs confirm Metal backend is in use.
- At least one problem triggers Claude API escalation; system falls back gracefully (no crash) when `ANTHROPIC_API_KEY_REAL` is absent.
- Stall escalation rate is below 30% of total calls (if above, thresholds need recalibration before cloud deployment).
- All Phase 0–3 exit criteria still pass after porting (regression test suite runs on mini).

### Phase 5 — Concurrency Hardening and Cloud (Weeks 11–12)

**Goal:** OAK handles multiple simultaneous problems without resource exhaustion, data leakage, or coordination race conditions.

**Scope:** Deploy TRUNK + GROVE to a cloud multi-GPU node. Replace Ollama with vLLM for concurrent throughput. Add Kubernetes overlay. Test 3–5 concurrent problems with resource caps enforced.

**Exit criteria (all must pass):**
- Three concurrent problems run to completion with no data leakage between worktrees (verified by cross-problem query test).
- Resource caps (`MAX_AGENTS_PER_PROBLEM`, `MAX_CONCURRENT_PROBLEMS`, `MAX_HARNESS_CONTAINERS`) are enforced and observable in `GET /api/telemetry`.
- vLLM serves the 70B model with at least 2 concurrent requests without OOM.
- Skill library aggregates correctly across concurrent problem solves (no race condition in promotion logic).
- Fewer than 1 unexpected failure per 10 concurrent problem runs.

---

## 15. Observability

Telemetry is only useful if it is tracked from the beginning. The following baseline metrics must be queryable from `agent_telemetry` and Redis at every phase.

### 15.1 Per-Problem Metrics

| Metric | Source | Why it matters |
|---|---|---|
| Total tokens consumed | `agent_telemetry.tokens_in + tokens_out` | Cost proxy; tracks efficiency trends |
| Wall-clock time per task type | `tasks.completed_at - claimed_at` | Identifies bottlenecks; measures skill reuse benefit |
| Failures per 10 problems | `agent_telemetry.success = FALSE` | System reliability signal |
| Stall escalations per problem | `oak:telemetry:escalations` (Redis counter) | Proxy calibration signal; should be <30% |
| Skill reuse rate | `skills.use_count` delta across problem | Primary compounding metric |
| Judge FAIL rate | `judge_verdicts.verdict = 'fail'` | Code quality signal per agent |

### 15.2 System-Level Metrics

| Metric | Source | Alert threshold |
|---|---|---|
| Active harness containers | `docker ps --filter name=oak-agent` | > `MAX_HARNESS_CONTAINERS` |
| Redis memory usage | `redis-cli info memory` | > 80% configured maxmemory |
| PostgreSQL connection pool | `pg_stat_activity` | > 80% `max_connections` |
| Ollama model load time | Proxy request logs | > 30s (model not pre-loaded) |
| Skill library size (permanent) | `skills` table WHERE status='permanent' | Monitored for growth; no threshold |

### 15.3 Phase-Gate Metrics

Each phase gate review checks these metrics to confirm health before advancing:

- **Phase 0 → 1:** API error rate < 1% on 100 test requests; schema constraint violation count = 0.
- **Phase 1 → 2:** Harness unit test pass rate = 100%; tool-proxy block rate on denied commands = 100%.
- **Phase 2 → 3:** Coordination failure rate < 2 per 10 problems; no task closure without Judge PASS.
- **Phase 3 → 4:** Skill reuse demonstrated on ≥ 1 problem class; Hub WebSocket stream latency < 500ms.
- **Phase 4 → 5:** Stall escalation rate < 30%; Mac Mini lifecycle success rate ≥ 8/10 problems.

---

## 16. Failure Mode Reference

The following table covers the most operationally significant failure modes. For each: what the system does, and what the operator should do.

| Failed component | System behaviour | Operator action |
|---|---|---|
| **Redis is down** | Session state restore fails silently; agents start with blank context but continue. Mailbox pub/sub is unavailable — agents cannot communicate. | `docker restart oak-redis`. Active agent sessions will lose context and stall; re-run `new-problem.sh` to restart with fresh state. |
| **PostgreSQL is down** | `POST /api/problems` returns 503. Task list and mailbox writes fail. All agents block on task claims. Judge verdicts cannot be recorded. | `docker restart oak-postgres`. PostgreSQL state is durable (mounted volume); no data is lost. Resume in-progress problems after restart. |
| **Ollama model not pulled** | Proxy receives a 404 or empty response from Ollama; if `STALL_DETECTION_ENABLED=true` and API key is present, escalates to Claude API. If not, proxy returns error to Claude Code and the agent stalls. | `docker exec oak-ollama ollama pull <model>`. The agent will retry on the next tool call. Bootstrap script pulls all required models — run it if models are missing. |
| **Ollama OOM (model too large)** | Ollama returns 500. Proxy escalates if configured; otherwise agents stall. | Switch to a smaller model in `.env` (`DEFAULT_MODEL`, `CODER_MODEL`). On DGX this should not occur with 128GB; on Mac Mini 64GB, avoid simultaneous 70B loads. |
| **oak-api-proxy unreachable** | Claude Code receives connection refused on its `ANTHROPIC_BASE_URL`. All agent tool calls fail immediately. | `docker restart oak-api-proxy`. This service is stateless — restart is safe and fast. |
| **Claude API key absent or expired** | If `STALL_DETECTION_ENABLED=false`: no effect (proxy never uses the key). If `true`: escalation fails; proxy logs `oak:telemetry:escalation_failures`, retries locally with adjusted prompt, and continues with Ollama response. | Check `ANTHROPIC_API_KEY_REAL` in `.env`. Expired key: rotate and restart proxy. No key: set `STALL_DETECTION_ENABLED=false` until a key is available. |
| **Judge Agent fails to respond** | `task-completed.sh` hook blocks task closure indefinitely. Problem stalls at validate stage. | Check agent telemetry for Judge agent errors. Re-invoke Judge manually: `docker run oak/harness:latest -e OAK_AGENT_ID=judge`. Alternatively, mark a manual PASS verdict in `judge_verdicts` for unblocking. |
| **Harness container exceeds `MAX_HARNESS_CONTAINERS`** | `new-problem.sh` refuses to launch a new harness container and returns an error. New problems cannot start. | Wait for active problems to complete, or manually stop idle containers (`docker ps --filter name=oak-agent`). Raise `MAX_HARNESS_CONTAINERS` in `.env` if hardware permits. |
| **Git worktree conflict** | `git worktree add` fails if branch already exists. `new-problem.sh` exits with error — no agent is started. | Run `git worktree list` to identify stale worktrees. Remove with `git worktree remove <path> --force` then re-run `new-problem.sh`. |

---

## 17. What Makes OAK Genuinely New

**Persistent skill compounding.** Most agent systems reason from scratch every time. OAK's Voyager-pattern skill library means the system is categorically more capable after 50 problems than after 5 — not because of fine-tuning, but because it has compiled executable knowledge from experience. The difference is like the difference between a junior engineer who has read the textbook and a senior engineer who has built fifty systems.

**Resource-aware grove.** Agent count is not fixed, but it is purposefully bounded. A simple ETL problem might spawn three agents; a multi-modal forecasting problem with six data sources might spawn twenty. The grove grows to match the problem within configured resource caps — not because ceilings are philosophically good, but because unconstrained growth on finite hardware is not growth at all.

**Self-evolving interface.** The Hub UI is not a finished product — it is a living thing that adds new pages and widgets as the agent grove encounters new problem classes and masters them. The interface reflects what OAK has become, not what it was designed to be.

**Sovereign intelligence.** Every skill, every memory, every learned pattern belongs to the operator and lives on their hardware. The system's growing domain expertise is not shared with any cloud provider, not subject to external policy changes, and not reset by a platform update.

**Hardware agnostic.** One codebase, one environment variable, three deployment targets. OAK grows where you plant it.

---

*Specification synthesised from: FORGE_system_framing.md, critically review and improvise the framing.md, revamp1.md (FABRIC), revamp2.md (OAK)*
*Remote repository: https://github.com/SharathSPhD/oak.git*
*Generated for Claude Code initialisation on NVIDIA DGX Spark*
