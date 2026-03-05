# ACORN — Adaptive Collaborative Orchestration and Reasoning Network

## Project Specification v1.0 · March 2026

> *From a single seed of intent, a network of reasoning agents grows outward,
> each branch strengthening the whole — every problem solved leaves the grove
> wiser, faster, and more capable than before.*

**Remote repository:** https://github.com/SharathSPhD/acorn.git  
**Primary platform:** NVIDIA DGX Spark (Apple Silicon Mac Mini M4 and Cloud GPU are profiles)  
**Agent runtime:** Claude Code agent teams via acorn-harness  
**Frontend:** Next.js Hub (port 8501)  
**Version history:**
- **v1.0** — Initial specification. Seven-layer stack, nine-agent catalogue, kernel grove, self-evolution boundaries, exit criteria (no phases).

---

## 1. Project Overview and Objectives

### 1.1 What ACORN Is

ACORN is a **self-evolving autonomous knowledge-work factory**. It extends OAK from a data-to-dashboard factory into a **general-purpose knowledge-work factory**. It accepts raw inputs — natural-language goals, documents, datasets, API endpoints, web sources — and produces high-quality, structured knowledge artefacts: analytical reports, decision recommendations, synthesised literature summaries, business intelligence dashboards, workflow automation scripts, and deployed interactive applications.

Where OAK specialises in data-to-dashboard pipelines for structured analytical problems, ACORN operates across the full spectrum of knowledge work:
- Unstructured document corpora → structured insights
- Multi-source research questions → cited, reasoned synthesis reports
- Business process descriptions → automated workflow scripts
- Raw metrics streams → adaptive monitoring dashboards
- Competitive intelligence requests → periodic briefing documents

Every problem ACORN solves is distilled into a reusable **ACORN Kernel** — a versioned, testable, composable skill unit stored in the permanent kernel grove. Future problems of the same class are resolved faster, with higher confidence, by orchestrating retrieved kernels rather than reasoning from scratch.

The name is deliberate. An acorn contains the full blueprint of an oak within a seed too small to see. ACORN the system starts small — a handful of agents, a modest kernel grove — but carries within its architecture the capacity to grow into an arbitrarily capable knowledge engine, bounded only by the operator's hardware and the quality of problems submitted to it.

### 1.2 Measurable Core Objectives

1. **Autonomous knowledge-work completion.** Given a natural-language goal and any combination of input artefacts, ACORN must produce a usable output artefact with no human involvement beyond the initial submission.

2. **Compounding kernel reuse.** For recurring knowledge-work classes, median time-to-first-useful-output must decrease by at least 50% after three similar problems have been solved. Kernels that cannot demonstrate reuse across at least two independent problems must not be promoted to permanent status.

3. **Reasoning transparency.** Every output artefact must be accompanied by a `REASONING_TRAIL.md` that records agent decisions, source attributions, kernel retrievals, and judge verdicts. The operator must be able to audit any output without reading agent logs.

4. **Data sovereignty and privacy.** All problem data, intermediate reasoning, agent memory, and compiled kernels remain on operator-owned hardware. Cloud escalation (Claude API) is optional, stateless, and never retains problem context.

5. **Platform portability.** ACORN must run identically on DGX Spark, Mac Mini M4, and cloud GPU instances using only `ACORN_MODE`. No application code changes are permitted between platforms.

6. **Self-evolving capability surface.** The Hub UI must reflect ACORN's current mastered problem classes. As new classes are solved, new Hub sections appear via automated PRs. The operator's only responsibility is merging those PRs.

### 1.3 Design Principles

**DGX Spark first.** ACORN is optimised for NVIDIA DGX Spark as the primary development and production target. Mac Mini M4 and cloud GPU are fully supported profiles but are not the design centre.

**Sovereign compute.** No problem data, agent memory, compiled kernels, or reasoning traces leave the operator's hardware. Cloud escalation is a quality-improvement option, never a correctness requirement.

**Resource-aware agent spawning.** The Orchestrator spawns as many agents as the problem requires, up to the configured maximum. Resource caps are tuning knobs, not architectural philosophy.

**No security anti-patterns.** ACORN uses Docker network isolation. It contains no components derived from OpenClaw, no third-party messaging integrations, and no complex authentication layers. It is designed for a single trusted operator on a private network.

**Reasoning as a first-class output.** ACORN treats structured reasoning (reports, recommendations, synthesised briefs) as equally valid top-level outputs. The Judge validates both code artefacts and document artefacts.

**Composable kernel architecture.** ACORN Kernels are more than SKILL.md files. Each kernel is a testable, versioned unit containing: a natural-language description, an executable Python module or shell script, a unit test suite, and a benchmark result from the last verified application. Kernels compose — a complex problem may retrieve and chain three kernels in sequence.

### 1.4 Self-Evolution Boundaries

**Autonomous (no human approval):**
- Kernel promotion after 2 verified uses
- Agent task plans
- Session state, telemetry, memory writes
- Spawn/terminate agents within caps
- Kernel retrieval, chaining, performance index updates

**Requires PR + human merge:**
- New Hub pages
- Agent prompt amendments
- Judge validation rule changes
- Kernel deprecation
- New kernel categories

**Requires explicit operator action:**
- Schema migrations
- TRUNK API surface changes
- Docker Compose changes
- Resource cap changes
- Enabling/disabling cloud escalation

### 1.5 WARDEN Scope

WARDEN is an **infra-only daemon**. It has:
- **No LLM** — no reasoning, no agent logic
- **No self-build** — no OAK builder, no cortex, no code generation
- **Only:** health checks, container restart, orphan cleanup, kernel index maintenance, research cache pruning, Calibration Agent triggers (when enabled)

---

## 2. System Architecture

### 2.1 Layer Map (7-Layer Stack)

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 7: CANOPY — Next.js Hub UI (port 8501)                       │
│  Problem submission · Live reasoning stream · Output gallery        │
│  Kernel library · Telemetry · Reasoning trail viewer               │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 6: GROVE — Agent Engine (acorn-harness containers)           │
│  Orchestrator · Research Analyst · Synthesis Agent · Domain         │
│  Specialist · Validator · Judge · Kernel Extractor · Interface       │
│  Agent · Calibration Agent                                          │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 5: RELAY — API Proxy (port 9000)                             │
│  acorn-api-relay: routes Claude Code → Ollama or Claude API        │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 4: WARDEN — Self-healing Daemon (infra only)                 │
│  acorn-warden: health checks · container restart · orphan cleanup   │
│  kernel index maintenance · research cache prune                    │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3: TRUNK — FastAPI Gateway (port 8000)                       │
│  /api/problems · /api/agents · /api/tasks · /api/kernels           │
│  /api/telemetry · /api/research · /api/reasoning · /api/mailbox     │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2: ROOTS — Persistence Layer                                 │
│  acorn-postgres (PostgreSQL 16 + pgvector) · acorn-redis (Redis 7)  │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 1: SOIL — Hardware                                            │
│  DGX Spark (PRIMARY) · Mac Mini M4 · Cloud GPU                      │
│  acorn-ollama (or vLLM in cloud) · Local inference by default       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Architectural Invariants

1. **CANOPY holds no agent logic and no problem data.** The Hub is a thin consumer of TRUNK API endpoints. The only state the Hub maintains locally is the browser session.

2. **All agent API calls route through RELAY.** No agent container has a direct network path to Ollama, Claude API, or any external endpoint. acorn-api-relay is the sole egress point for inference traffic.

3. **TRUNK is the sole writer to ROOTS for schema-level data.** Agents write to working memory (Redis) and the problem worktree (filesystem). They do not issue DDL or direct PostgreSQL writes outside of MCP server calls.

4. **Every kernel is testable in isolation.** A kernel that cannot be exercised by its own unit test suite without a running ACORN stack is not a valid kernel and will not be promoted to permanent status.

5. **WARDEN never modifies agent logic.** The daemon is an infrastructure service only. It restarts containers, cleans orphans, and updates the kernel performance index. It does not amend prompts or modify kernel content.

### 2.3 Agent Model Routing

| Role | Default Model | Purpose |
|------|---------------|---------|
| orchestrator | qwen3-coder | Problem decomposition |
| research-analyst | qwen2.5:14b | Web research, document retrieval |
| synthesis-agent | qwen3-coder | Reasoning synthesis, report drafting |
| domain-specialist | qwen2.5:14b | Deep domain reasoning |
| validator | qwen2.5:14b | Output validation |
| judge | qwen3-coder | Final PASS/FAIL — always local |
| kernel-extractor | qwen2.5:14b | Pattern extraction |
| interface-agent | qwen2.5:14b | UI code generation |
| calibration-agent | qwen3-coder | Prompt analysis |

Override any model via env: `SYNTHESIS_MODEL=deepseek-r1:14b bash scripts/bootstrap.sh dgx`

### 2.4 Redis Channels

| Channel | Purpose | Publisher | Subscribers |
|---------|---------|-----------|-------------|
| `acorn:stream:{problem_id}` | Live agent events | All agents via hook | Hub WebSocket, telemetry |
| `acorn:mailbox:{agent_id}` | Peer-to-peer messages | Any agent | Named recipient |
| `acorn:broadcast:{problem_id}` | Task announcements | Orchestrator | All agents for problem |
| `acorn:blocked:{agent_id}` | Denied tool call log | tool-proxy.sh | Security telemetry |
| `acorn:kernel:notify` | New kernel available | Kernel Extractor | Orchestrator |
| `acorn:reasoning:{problem_id}` | Reasoning step events | All agents | Trail recorder |

Event envelope schema (all channels):
```json
{
  "event_type": "string",
  "agent_id": "string",
  "problem_id": "string",
  "timestamp_utc": 1234567890.123,
  "schema_version": "1.0",
  "payload": {}
}
```

---

## 3. Repository Structure and Git Worktrees

### 3.1 Branch Map

| Branch | Worktree path | Purpose |
|--------|---------------|---------|
| `main` | `acorn/` | Stable core: Docker configs, schema DDL, FastAPI, shared libs |
| `acorn/agents` | `acorn-workspaces/agents` | Agent definitions, CLAUDE.md per agent, hook scripts |
| `acorn/kernels` | `acorn-workspaces/kernels` | Kernel grove: KERNEL.md files, Python modules, test suites |
| `acorn/ui` | `acorn-workspaces/ui` | Next.js Hub |
| `acorn/problem-{uuid}` | `acorn-workspaces/problem-{uuid}` | Per-problem isolated workspace |

### 3.2 Directory Layout (main branch)

```
acorn/
├── .claude/
│   ├── CLAUDE.md
│   ├── agents/
│   │   ├── orchestrator.md
│   │   ├── research-analyst.md
│   │   ├── synthesis-agent.md
│   │   ├── domain-specialist.md
│   │   ├── validator.md
│   │   ├── judge-agent.md
│   │   ├── kernel-extractor.md
│   │   ├── interface-agent.md
│   │   └── calibration-agent.md
│   ├── hooks/
│   │   ├── pre-tool-use.sh
│   │   ├── post-tool-use.sh
│   │   ├── task-completed.sh
│   │   ├── teammate-idle.sh
│   │   └── reasoning-step.sh
│   ├── mcp.json
│   └── settings.json
├── api/
│   ├── main.py, config.py (AcornSettings), dependencies.py, models.py
│   ├── routers/
│   │   ├── problems.py
│   │   ├── agents.py
│   │   ├── tasks.py
│   │   ├── kernels.py
│   │   ├── telemetry.py
│   │   ├── research.py
│   │   ├── reasoning.py
│   │   └── mailbox.py
│   ├── factories/agent_factory.py
│   ├── events/bus.py
│   ├── state_machines/ (task.py, problem.py)
│   ├── lifecycle/agent_lifecycle.py
│   └── db/schema.sql
├── memory/
│   ├── interfaces.py
│   ├── kernel_repository.py
│   ├── episodic_repository.py
│   ├── reasoning_trail.py
│   ├── cached_kernels.py
│   └── validation_chain.py
├── acorn_mcp/
│   ├── acorn-memory-mcp/
│   ├── acorn-kernels-mcp/
│   ├── acorn-research-mcp/
│   └── acorn-api-relay/
├── docker/
│   ├── acorn-harness/
│   ├── warden/
│   ├── docker-compose.yml
│   ├── docker-compose.dgx.yml
│   ├── docker-compose.mini.yml
│   └── docker-compose.cloud.yml
├── ui-next/                    # Next.js CANOPY app
├── tests/
├── scripts/
│   ├── bootstrap.sh
│   ├── new-problem.sh
│   ├── merge-solution.sh
│   └── cleanup-orphans.sh
├── pyproject.toml
├── .env.example
├── QUICKSTART.md
├── USER_MANUAL.md
├── spec.md
└── PRD.md
```

---

## 4. Claude Code Scaffolding

### 4.1 Root CLAUDE.md

```markdown
# ACORN — Adaptive Collaborative Orchestration and Reasoning Network

You are operating within the ACORN system on a {ACORN_MODE} node.

## Runtime Environment (Critical)

Claude Code connects to local models via these environment variables — set by the
acorn-harness container and must NOT be overridden:

  ANTHROPIC_BASE_URL=http://acorn-api-relay:9000   # ACORN dynamic routing relay
  ANTHROPIC_AUTH_TOKEN=ollama                       # Required for Ollama compat
  ANTHROPIC_API_KEY=                                # Explicitly empty; relay manages real key

To invoke: `claude --model qwen2.5:14b --workspace /workspace`
Alternative models: `qwen3-coder` (reasoning), `qwen2.5:14b` (research), `llama3.3:70b` (synthesis)

The `acorn-api-relay` routes each call to Ollama or Claude API automatically
based on task type and response confidence. You do not need to manage this.

## Your Role (when invoked as Team Lead / Orchestrator)

1. Read the problem statement and input manifest from the current problem worktree.
2. Decompose the problem into typed tasks using TaskCreate.
3. Determine the required agent specialisations (research, synthesis, domain, validate).
4. Spawn specialist teammates for each task class.
5. Monitor the shared task list and synthesise outputs into the final artefact.
6. Invoke the Judge Agent before any solution is marked complete.

## Environment

- API relay (your Anthropic endpoint): http://acorn-api-relay:9000
- Ollama (local models): http://acorn-ollama:11434
- PostgreSQL: postgresql://acorn:acorn@acorn-postgres:5432/acorn
- Redis: redis://acorn-redis:6379 (also holds your session state)
- Kernel grove: /acorn-workspaces/kernels/
- Problem workspace: /acorn-workspaces/problem-{PROBLEM_UUID}/
- Research cache: /acorn-workspaces/research-cache/

## Agent Team Setup

  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
  Team name convention: acorn-{PROBLEM_UUID}
  Task folder: .claude/tasks/acorn-{PROBLEM_UUID}

## Available Subagents

See `.claude/agents/` — invoke by name, e.g., `use agent research-analyst`.

## Session State

Your session state (open files, command history, git state, kernel retrievals,
reasoning chain so far) persists in Redis under `acorn:session:{AGENT_ID}`.
The harness restores this at session start. You do not need to re-establish
context from scratch between invocations.

## MCP Servers (see .claude/mcp.json)

- `filesystem`: read/write access to /workspace and /acorn-workspaces/kernels
- `postgres`: full DB access via MCP (never raw psql from agent code)
- `git`: repository operations
- `acorn-memory`: pgvector episodic memory retrieval
- `acorn-kernels`: kernel grove lookup and retrieval
- `acorn-research`: web search, document fetch, URL content extraction

## Hooks (auto-run, do not disable)

All hooks are in `.claude/hooks/`. They run automatically.
- `pre-tool-use.sh`: deny-list (layer 2 after tool-proxy)
- `post-tool-use.sh`: telemetry + session state
- `task-completed.sh`: blocks closure without Judge PASS; triggers kernel extraction
- `teammate-idle.sh`: re-focus on idle (>120s without tool call)
- `reasoning-step.sh`: records every significant reasoning decision to trail

## Rules

- Never drop tables or delete files without a pre-tool-use hook approval.
- Never commit to `main` directly — always use `acorn/problem-{uuid}` branch.
- Always run the Judge Agent before marking a problem TaskCompleted.
- Log all tool invocations via post-tool-use hook (automated).
- No third-party messaging integrations. No external API calls except through
  acorn-api-relay.
- Every significant reasoning step must emit a `reasoning-step` event via the hook.
- When retrieving kernels, always check permanent grove first via acorn-kernels MCP.
  Do not re-derive what the kernel grove already contains.
- The REASONING_TRAIL.md file must be written to the problem worktree before the
  Judge is invoked. It is a required input to the Judge's verdict.
```

### 4.2 MCP Server Configuration (.claude/mcp.json)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/workspace", "/acorn-workspaces/kernels",
               "/acorn-workspaces/research-cache"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://acorn:acorn@acorn-postgres:5432/acorn"]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/home/acorn"]
    },
    "acorn-memory": {
      "command": "python3",
      "args": ["/home/acorn/acorn_mcp/acorn-memory-mcp/server.py"]
    },
    "acorn-kernels": {
      "command": "python3",
      "args": ["/home/acorn/acorn_mcp/acorn-kernels-mcp/server.py"]
    },
    "acorn-research": {
      "command": "python3",
      "args": ["/home/acorn/acorn_mcp/acorn-research-mcp/server.py"]
    }
  }
}
```

### 4.3 Agent Definitions (.claude/agents/)

Each file in `.claude/agents/` defines a Claude Code subagent with a constrained persona, specific tool access, and a declared `__pattern__` compatible with the PRD's design pattern registry.

#### orchestrator.md

```markdown
***
name: orchestrator
description: Team Lead. Decomposes problems, assigns tasks, spawns specialist agents, monitors progress, synthesises final output. Invokes Judge before closure.
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__acorn-memory
  - mcp__filesystem
  - mcp__git
***

# Orchestrator — Team Lead

## Identity

You are the Orchestrator, the team lead for ACORN problem-solving. You read the problem manifest, query the kernel grove for relevant prior kernels, decompose the problem into typed tasks (research, synthesise, domain-analyse, validate, deliver), assign tasks to appropriate specialist agents, monitor progress via the task list, and synthesise final output. You must emit a reasoning step event for every decomposition decision.

## Lifecycle

1. **RESTORE** — session state restored automatically from Redis
2. **ORIENT** — read PROBLEM.md, input manifest, output format
3. **KERNEL QUERY** — query acorn-kernels MCP for kernels matching this problem class
4. **DECOMPOSE** — create typed tasks in PostgreSQL, write task briefs to .claude/tasks/acorn-{PROBLEM_UUID}/
5. **SPAWN** — invoke research-analyst, domain-specialist (if needed), synthesis-agent, validator, judge-agent in sequence
6. **MONITOR** — read mailbox, task status, synthesise outputs
7. **CLOSE** — invoke Judge; on PASS, mark task complete; trigger kernel-extractor

## Output Contract

- orchestrator_plan.md in task folder
- status.json updated after each agent completes
- REASONING_TRAIL.md populated via reasoning-step.sh (you emit steps)

## Constraints

- Never skip the Judge. A task cannot be TaskCompleted without Judge PASS.
- Always check kernel grove before reasoning from scratch.
```

#### research-analyst.md

```markdown
***
name: research-analyst
description: Information gathering specialist. Claims research tasks. Queries acorn-research MCP for web search and document fetches. Writes RESEARCH.md with citations. Forbidden from synthesising conclusions.
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__acorn-research
  - mcp__filesystem
***

# Research Analyst

## Identity

You are the Research Analyst. You claim `research` tasks. You query `acorn-research` MCP for web search results and document fetches. You extract structured information from unstructured sources. You write `RESEARCH.md` (citations, extracted facts, confidence scores per source) to the problem worktree. You are forbidden from synthesising conclusions — your output is raw sourced information only. If a research kernel exists for the query type, use it rather than re-deriving the search strategy.

## Lifecycle

1. RESTORE, ORIENT, KERNEL QUERY (as per root CLAUDE.md)
2. **EXECUTE** — run web search, fetch documents, extract facts, assign confidence per source
3. **REPORT** — write RESEARCH.md with citations
4. CLOSE, SAVE

## Output Contract

- RESEARCH.md: structured list of sources, snippets, confidence scores, no conclusions

## Constraints

- No synthesis. No recommendations. Only sourced facts.
```

#### synthesis-agent.md

```markdown
***
name: synthesis-agent
description: Reasoning and drafting specialist. Claims synthesise tasks. Reads RESEARCH.md and domain analysis. Produces primary knowledge artefact: report, recommendation, structured summary, or app skeleton. Writes SYNTHESIS.md or app.py.
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__acorn-memory
  - mcp__filesystem
  - mcp__git
***

# Synthesis Agent

## Identity

You are the Synthesis Agent. You claim `synthesise` tasks. You read `RESEARCH.md` and any domain analysis outputs. You produce the primary knowledge artefact: report, recommendation document, structured summary, or Streamlit/Next.js app skeleton. You write `SYNTHESIS.md` or `app.py` to the problem worktree. Every synthesis step must be recorded as a reasoning event. You must not fabricate citations — all claims must trace to `RESEARCH.md` entries.

## Lifecycle

1. RESTORE, ORIENT, KERNEL QUERY
2. **EXECUTE** — read RESEARCH.md, DOMAIN_ANALYSIS.md (if present), apply synthesis kernel if found, draft artefact
3. **REPORT** — write SYNTHESIS.md or primary artefact
4. CLOSE, SAVE

## Output Contract

- SYNTHESIS.md or app.py (or equivalent primary artefact)
- All citations traceable to RESEARCH.md

## Constraints

- No fabricated citations. All claims must trace to RESEARCH.md.
```

#### domain-specialist.md

```markdown
***
name: domain-specialist
description: Deep domain reasoning. Claims domain-analyse tasks when Orchestrator identifies specialised domain (finance, legal, science, engineering). Writes DOMAIN_ANALYSIS.md. Flags uncertain claims with [UNCERTAIN].
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__acorn-memory
  - mcp__filesystem
***

# Domain Specialist

## Identity

You are the Domain Specialist. You claim `domain-analyse` tasks when the Orchestrator identifies a specialised domain (financial modelling, legal interpretation, scientific literature, engineering specifications). You read domain context from the problem worktree plus retrieved episodic memory from prior domain problems. You write `DOMAIN_ANALYSIS.md`. You maintain a strict factual discipline — if confidence in a domain claim is below 0.7, you must flag the claim as `[UNCERTAIN]` in your output rather than asserting it.

## Lifecycle

1. RESTORE, ORIENT, KERNEL QUERY
2. **EXECUTE** — analyse domain context, retrieve episodic memory, write DOMAIN_ANALYSIS.md
3. **REPORT** — write DOMAIN_ANALYSIS.md with [UNCERTAIN] flags where appropriate
4. CLOSE, SAVE

## Output Contract

- DOMAIN_ANALYSIS.md: domain-specific insights, [UNCERTAIN] for low-confidence claims

## Constraints

- Confidence < 0.7 → [UNCERTAIN] flag. Never assert uncertain claims as fact.
```

#### validator.md

```markdown
***
name: validator
description: Output validation specialist. Claims validate tasks. Checks structural, factual, and executable (for code) validation. Writes VALIDATION_REPORT.md. Blocks Judge until all layers pass.
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__filesystem
***

# Validator

## Identity

You are the Validator. You claim `validate` tasks. You check the primary artefact against three validation layers:
1. **Structural**: required sections present, formatting correct, no empty placeholders
2. **Factual**: all citations trace to RESEARCH.md; [UNCERTAIN] claims appropriately hedged
3. **Executable** (for code): ruff check, mypy --strict, smoke test; for Streamlit/Next.js, verify run completes

You write `VALIDATION_REPORT.md` to the problem worktree. A failed validation blocks the Judge from issuing PASS. If all three layers pass, emit `validation_complete` and notify Judge via mailbox.

## Lifecycle

1. RESTORE, ORIENT
2. **EXECUTE** — run structural, factual, executable checks
3. **REPORT** — write VALIDATION_REPORT.md
4. CLOSE, SAVE

## Output Contract

- VALIDATION_REPORT.md: structural, factual, executable results

## Constraints

- All three layers must pass before Judge can issue PASS.
```

#### judge-agent.md

```markdown
***
name: judge-agent
description: Quality gate. Reads REASONING_TRAIL.md, VALIDATION_REPORT.md, primary artefact. Issues PASS or FAIL verdict. Judge runs fully locally — never escalates to Claude API.
tools:
  - Read
  - mcp__postgres
  - mcp__filesystem
***

# Judge Agent

## Identity

You are the Judge. You read `REASONING_TRAIL.md`, `VALIDATION_REPORT.md`, and the primary artefact. You issue a structured `PASS` or `FAIL` verdict with granular check results posted to `judge_verdicts` table and the mailbox. A task cannot be marked `TaskCompleted` until you post PASS. If FAIL, you must identify exactly which agent produced the failing output and re-task that agent specifically. You run fully locally — you are the one agent role that must never escalate to Claude API.

## Lifecycle

1. RESTORE, ORIENT
2. **EXECUTE** — read trail, validation report, artefact; evaluate; post verdict
3. **REPORT** — write to judge_verdicts, mailbox
4. CLOSE, SAVE

## Output Contract

- judge_verdicts row: verdict, checks, reasoning, failing_agent (if FAIL)

## Constraints

- Never escalate. Always local model.
```

#### kernel-extractor.md

```markdown
***
name: kernel-extractor
description: Runs after every PASS verdict. Identifies reusable patterns from reasoning chain, research strategy, synthesis approach, or code. Writes KERNEL.md + Python module + test suite to probationary grove.
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__filesystem
  - mcp__git
***

# Kernel Extractor

## Identity

You run asynchronously after every PASS verdict. You read the problem worktree and identify reusable patterns from the reasoning chain, research strategy, synthesis approach, or code produced. You write candidate `KERNEL.md` entries plus a Python module and test suite to the probationary queue at `acorn-workspaces/kernels/probationary/`. You update the kernel index in PostgreSQL with metadata, trigger keywords, and a pgvector embedding of the kernel description. You enforce: a kernel must describe a pattern reusable across problem classes — it must not be a transcription of the specific problem's solution.

## Lifecycle

1. RESTORE, ORIENT (triggered by task-completed.sh on PASS)
2. **EXECUTE** — analyse worktree, extract pattern, write KERNEL.md, implementation, tests
3. **REPORT** — write to probationary/, update PostgreSQL
4. CLOSE, SAVE

## Output Contract

- KERNEL.md in probationary/
- Python module + test suite
- PostgreSQL kernels row (probationary status)

## Constraints

- Pattern must be reusable. No problem-specific transcription.
```

#### interface-agent.md

```markdown
***
name: interface-agent
description: UI evolution specialist. Activated when new problem class mastered. Generates new Next.js page code or widget additions. Opens PR against acorn/ui. Subject to churn limit: one UI PR per three problems.
tools:
  - Read
  - Write
  - Bash
  - mcp__postgres
  - mcp__acorn-kernels
  - mcp__filesystem
  - mcp__git
***

# Interface Agent

## Identity

You are the Interface Agent. You are activated when a new problem class is mastered (three consecutive PASSes for the same class). You read the Hub's current page structure and generate new Next.js page code or widget additions to represent the newly mastered class. You open a PR against `acorn/ui`. Subject to the churn limit: no more than one UI PR per three problems solved. If the PR churn limit is active, you queue the change and open it when the limit resets.

## Lifecycle

1. RESTORE, ORIENT (triggered by Orchestrator or WARDEN)
2. **EXECUTE** — read Hub structure, generate new page/widget code
3. **REPORT** — open PR against acorn/ui
4. CLOSE, SAVE

## Output Contract

- PR against acorn/ui with new page or widget

## Constraints

- Churn limit: one UI PR per three problems.
```

#### calibration-agent.md

```markdown
***
name: calibration-agent
description: Prompt improvement specialist. Runs on schedule (daily or every 10 problems). Reads agent_telemetry for failure patterns. Proposes prompt amendments. Opens PR against acorn/agents. Never self-applies.
tools:
  - Read
  - Write
  - mcp__postgres
  - mcp__filesystem
  - mcp__git
***

# Calibration Agent

## Identity

You are the Calibration Agent. You run on schedule (daily or after every ten problems). You read `agent_telemetry` for recurring failure patterns: high re-task rates, low judge scores, excessive reasoning steps for simple problems. You propose targeted prompt amendments for the affected agent. You open a PR against `acorn/agents` for human review. You never self-apply your own amendments — all changes require a human merge.

## Lifecycle

1. RESTORE, ORIENT (triggered by WARDEN)
2. **EXECUTE** — analyse telemetry, identify patterns, draft amendments
3. **REPORT** — open PR against acorn/agents
4. CLOSE, SAVE

## Output Contract

- PR against acorn/agents with prompt amendments

## Constraints

- Never self-apply. Human merge required.
```

### 4.4 Kernel Grove Format and Lifecycle

**Kernel file format (KERNEL.md):**

```markdown
***
name: {kernel-name}
version: 1.0.0
category: {research|synthesis|domain|validation|code|workflow}
status: probationary|permanent|deprecated
trigger_keywords: [comma-separated terms for semantic retrieval]
verified_on_problems: [list of problem UUIDs]
benchmark:
  last_run: {ISO timestamp}
  median_execution_ms: {number}
  pass_rate: {0.0–1.0}
  problems_tested: {count}
created_at: {ISO timestamp}
promoted_at: {ISO timestamp or null}
deprecated_at: {ISO timestamp or null}
deprecation_reason: {string or null}
***

## Description

Plain English description of what this kernel does and when to use it.

## Prerequisites

- Required environment variables, Python packages, input artefacts

## Composition

List any other kernels this kernel depends on or chains with.

## Implementation

```python
# Full executable Python module. Must be importable without running ACORN stack.
__pattern__ = "Strategy"

from typing import Any

def execute(inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute the kernel against the given inputs."""
    ...
```

## Tests

```python
# Unit test suite. Must pass: pytest kernel_name_test.py -v
def test_kernel_name__standard_input__produces_expected_output():
    ...
```

## Known Edge Cases

Explicit list of known failure modes and handling strategy.

## Do Not Use When

Contra-indications — problem classes where this kernel produces poor results.

## Changelog

- v1.0.0 — Initial promotion. Verified on {problem_uuid_1}, {problem_uuid_2}.
```

**Kernel lifecycle:**
```
Kernel Extractor writes KERNEL.md
          ↓
  probationary/
  (indexed in PostgreSQL, retrievable but not auto-applied)
          ↓
  Applied to Problem #2 (independent) → PASS verdict
          ↓
  use_count >= ACORN_KERNEL_PROMO_THRESHOLD (default: 2)
          ↓
  PromotionRequest raised by KernelRepository
          ↓
  permanent/
  (auto-retrieved by Orchestrator for matching future problems)
          ↓
  If benchmark pass_rate drops below KERNEL_DEPRECATION_THRESHOLD (default: 0.4)
  over trailing 10 uses → deprecation PR
          ↓
  deprecated/ (never deleted — archived for audit)
```

### 4.5 Lifecycle Hooks (.claude/hooks/)

#### pre-tool-use.sh

```bash
#!/bin/bash
# Layer 2 deny-list. Runs before any tool invocation.
# Layer 1 is tool-proxy.sh inside harness container.
set -euo pipefail

CMD="${ACORN_TOOL_CMD:-}"
AGENT="${ACORN_AGENT_ID:-unknown}"
PROBLEM="${ACORN_PROBLEM_UUID:-unknown}"

# Acorn-specific business rules beyond hard system deny-list
# Blocks: git push --force to main/agents/kernels/ui
# Blocks: writes outside /workspace and /acorn-workspaces/problem-{PROBLEM_UUID}/
# Blocks: curl/wget to non-relay endpoints
# Blocks: DROP TABLE, DROP DATABASE, TRUNCATE in SQL

if echo "$CMD" | grep -qiE "git\s+push\s+--force\s+(origin\s+)?(main|acorn/agents|acorn/kernels|acorn/ui)"; then
  echo "ACORN-PRE-TOOL BLOCKED: force push to protected branch" >&2
  exit 2
fi

if echo "$CMD" | grep -qiE "DROP\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE"; then
  echo "ACORN-PRE-TOOL BLOCKED: destructive SQL" >&2
  exit 2
fi

# POST to TRUNK for full validation (hook is thin relay)
curl -sf -X POST "http://acorn-api:8000/internal/hooks/pre-tool-use" \
  -H "Content-Type: application/json" \
  -d "{\"cmd\":\"${CMD}\",\"agent_id\":\"${AGENT}\",\"problem_id\":\"${PROBLEM}\"}" \
  && exit 0 || exit 2
```

#### post-tool-use.sh

```bash
#!/bin/bash
# Runs after every tool call. Records telemetry, updates session state, publishes stream event.
set -euo pipefail

# POST serialised AgentEvent to TRUNK
curl -sf -X POST "http://acorn-api:8000/internal/events" \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
  "event_type": "tool_use",
  "agent_id": "${ACORN_AGENT_ID}",
  "problem_id": "${ACORN_PROBLEM_UUID}",
  "tool_name": "${ACORN_TOOL_NAME}",
  "duration_ms": ${ACORN_DURATION_MS:-0},
  "success": ${ACORN_SUCCESS:-true},
  "timestamp_utc": $(date +%s).$(date +%N | cut -c1-3)
}
EOF
```

#### task-completed.sh

```bash
#!/bin/bash
# Fires when agent attempts to close a task. Blocks closure without Judge PASS.
set -euo pipefail

TASK_ID="${ACORN_TASK_ID:-}"
PROBLEM_ID="${ACORN_PROBLEM_UUID:-}"

# Check judge_verdicts for PASS
PASS=$(curl -sf "http://acorn-api:8000/api/judge/verdict?task_id=${TASK_ID}" | jq -r '.verdict // "none"')

if [ "$PASS" != "pass" ]; then
  echo "ACORN-TASK-COMPLETED BLOCKED: Judge PASS required. Invoke Judge Agent first." >&2
  exit 2
fi

# Trigger kernel-extractor asynchronously
curl -sf -X POST "http://acorn-api:8000/internal/trigger-kernel-extract" \
  -H "Content-Type: application/json" \
  -d "{\"problem_id\":\"${PROBLEM_ID}\",\"task_id\":\"${TASK_ID}\"}" &

# Mark task complete
curl -sf -X POST "http://acorn-api:8000/api/tasks/${TASK_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"complete"}'

exit 0
```

#### teammate-idle.sh

```bash
#!/bin/bash
# Fires if no tool calls for > ACORN_IDLE_TIMEOUT_SECONDS (default: 120).
# Injects re-focus prompt.
set -euo pipefail

TIMEOUT="${ACORN_IDLE_TIMEOUT_SECONDS:-120}"
TASK_DESC="${ACORN_CURRENT_TASK:-unknown}"
LAST_STEP="${ACORN_LAST_REASONING_STEP:-none}"
KERNELS="${ACORN_KERNELS_RETRIEVED:-none}"

# Publish re-focus event to Redis for agent to consume
redis-cli -u "${REDIS_URL}" PUBLISH "acorn:mailbox:${ACORN_AGENT_ID}" \
  "{\"type\":\"refocus\",\"message\":\"You appear to be idle. Your current task is: ${TASK_DESC}. Last reasoning step: ${LAST_STEP}. Kernels retrieved: ${KERNELS}. Please continue or flag a blocker in the mailbox.\"}"
```

#### reasoning-step.sh

```bash
#!/bin/bash
# Called at significant decision points. Records step to Redis and flushes to REASONING_TRAIL.md on completion.
set -euo pipefail

STEP_TYPE="${ACORN_STEP_TYPE:-decision}"
SUMMARY="${ACORN_STEP_SUMMARY:-}"
CONFIDENCE="${ACORN_CONFIDENCE:-1.0}"
SOURCES="${ACORN_SOURCES:-[]}"

# Publish to acorn:reasoning:{problem_id}
redis-cli -u "${REDIS_URL}" PUBLISH "acorn:reasoning:${ACORN_PROBLEM_UUID}" \
  "{\"step_type\":\"${STEP_TYPE}\",\"summary\":\"${SUMMARY}\",\"confidence\":${CONFIDENCE},\"sources\":${SOURCES},\"agent_id\":\"${ACORN_AGENT_ID}\",\"ts\":$(date +%s)}"

# Also append to reasoning_steps table via API
curl -sf -X POST "http://acorn-api:8000/api/reasoning/steps" \
  -H "Content-Type: application/json" \
  -d "{\"problem_id\":\"${ACORN_PROBLEM_UUID}\",\"agent_id\":\"${ACORN_AGENT_ID}\",\"step_type\":\"${STEP_TYPE}\",\"summary\":\"${SUMMARY}\",\"confidence\":${CONFIDENCE},\"sources\":${SOURCES}}"
```

---

## 5. Harness and Relay

### 5.1 acorn-harness Dockerfile

```dockerfile
# docker/acorn-harness/Dockerfile

FROM node:20-slim

# Claude Code binary — full harness: subagents, kernels, agent teams, hooks, MCP
RUN npm install -g @anthropic-ai/claude-code

# Python for tool proxy, session state, and reasoning trail scripts
RUN apt-get update && apt-get install -y python3 python3-pip git curl jq \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir redis psycopg2-binary requests httpx

# ACORN-specific scripts
COPY scripts/tool-proxy.sh   /usr/local/bin/acorn-tool-proxy
COPY scripts/session-state.py /usr/local/bin/acorn-session
COPY scripts/deny-patterns.txt /etc/acorn/deny-patterns.txt
RUN chmod +x /usr/local/bin/acorn-tool-proxy /usr/local/bin/acorn-session

WORKDIR /workspace

# Canonical relay recipe
ENV ANTHROPIC_BASE_URL=http://acorn-api-relay:9000
ENV ANTHROPIC_AUTH_TOKEN=ollama
ENV ANTHROPIC_API_KEY=

ENTRYPOINT ["/bin/sh", "-c", \
  "python3 /usr/local/bin/acorn-session restore && \
   exec claude --model qwen2.5:14b --workspace /workspace"]
```

### 5.2 tool-proxy.sh

```bash
#!/bin/bash
# docker/acorn-harness/scripts/tool-proxy.sh
# Layer 1 deny-list interceptor — runs before pre-tool-use.sh hook
set -euo pipefail

CMD="${ACORN_TOOL_CMD:-}"
AGENT="${ACORN_AGENT_ID:-unknown}"
REDIS_URL="${REDIS_URL:-redis://acorn-redis:6379}"

while IFS= read -r pattern; do
  [[ -z "$pattern" || "$pattern" =~ ^# ]] && continue
  if echo "$CMD" | grep -qiE "$pattern"; then
    echo "ACORN-PROXY BLOCKED: matched deny pattern '$pattern'" >&2
    redis-cli -u "${REDIS_URL}" LPUSH "acorn:blocked:${AGENT}" \
      "{\"cmd\":\"${CMD}\",\"pattern\":\"${pattern}\",\"ts\":$(date +%s)}" \
      > /dev/null
    exit 2
  fi
done < /etc/acorn/deny-patterns.txt

redis-cli -u "${REDIS_URL}" LPUSH "acorn:session:${AGENT}:cmd_history" \
  "{\"cmd\":\"${CMD}\",\"ts\":$(date +%s)}" > /dev/null
redis-cli -u "${REDIS_URL}" LTRIM "acorn:session:${AGENT}:cmd_history" 0 49

exit 0
```

### 5.3 deny-patterns.txt

```
rm\s+-rf\s+/
DROP\s+TABLE
DROP\s+DATABASE
TRUNCATE\s+TABLE
chmod\s+777
curl\s+.*\s+[|>]\s*sh
wget\s+.*\s+[|>]\s*sh
git\s+push\s+--force\s+(origin\s+)?(main|acorn/agents|acorn/kernels|acorn/ui)
/dev/sd[a-z]
dd\s+if=
mkfs\.
```

### 5.4 session-state.py

```python
"""
Manages ACORN agent session state in Redis.
State keys: acorn:session:{agent_id}:open_files, cmd_history, cwd, git_state, kernels_used, reasoning_steps
All keys expire after ACORN_SESSION_TTL_HOURS (default: 24h).
"""
import sys
import json
import os
import redis

r = redis.from_url(os.environ["REDIS_URL"])
agent_id = os.environ.get("ACORN_AGENT_ID", "default")
ttl = int(os.environ.get("ACORN_SESSION_TTL_HOURS", 24)) * 3600

def restore() -> None:
    state: dict = {}
    cwd = r.get(f"acorn:session:{agent_id}:cwd")
    if cwd:
        state["cwd"] = cwd.decode()
        os.chdir(state["cwd"])
    git = r.hgetall(f"acorn:session:{agent_id}:git_state")
    if git:
        state["git"] = {k.decode(): v.decode() for k, v in git.items()}
    files = r.zrange(f"acorn:session:{agent_id}:open_files", 0, 9, withscores=True)
    if files:
        state["recent_files"] = [f.decode() for f in files]
    history = r.lrange(f"acorn:session:{agent_id}:cmd_history", 0, 9)
    if history:
        state["recent_commands"] = [json.loads(h) for h in history]
    kernels = r.lrange(f"acorn:session:{agent_id}:kernels_used", 0, -1)
    if kernels:
        state["kernels_retrieved_this_session"] = [k.decode() for k in kernels]
    reasoning = r.lrange(f"acorn:session:{agent_id}:reasoning_steps", 0, 4)
    if reasoning:
        state["last_reasoning_steps"] = [json.loads(s) for s in reasoning]
    if state:
        print(f"ACORN Session Restored:\n{json.dumps(state, indent=2)}")
    else:
        print(f"ACORN Session: fresh start for agent {agent_id}")

def save(key: str, value: str) -> None:
    full_key = f"acorn:session:{agent_id}:{key}"
    r.set(full_key, value)
    r.expire(full_key, ttl)

def record_kernel(kernel_name: str) -> None:
    list_key = f"acorn:session:{agent_id}:kernels_used"
    r.lpush(list_key, kernel_name)
    r.ltrim(list_key, 0, 49)
    r.expire(list_key, ttl)

def record_reasoning_step(summary: str, step_type: str) -> None:
    list_key = f"acorn:session:{agent_id}:reasoning_steps"
    r.lpush(list_key, json.dumps({"summary": summary, "type": step_type, "ts": __import__("time").time()}))
    r.ltrim(list_key, 0, 19)
    r.expire(list_key, ttl)

if __name__ == "__main__":
    if sys.argv[1] == "restore":
        restore()
    elif sys.argv[1] == "save" and len(sys.argv) >= 4:
        save(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "kernel" and len(sys.argv) >= 3:
        record_kernel(sys.argv[2])
    elif sys.argv[1] == "reasoning" and len(sys.argv) >= 4:
        record_reasoning_step(sys.argv[2], sys.argv[3])
```

### 5.5 acorn-api-relay (main.py)

```python
# acorn_mcp/acorn-api-relay/main.py
"""
ACORN API Relay — dynamic routing between Ollama and Claude API.
All routing decisions delegated to RoutingStrategy (Strategy pattern).
"""
__pattern__ = "Strategy"

import os
import json
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from strategies import get_routing_strategy

app = FastAPI(title="ACORN API Relay")

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://acorn-ollama:11434")
CLAUDE_URL = "https://api.anthropic.com"
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY_REAL", "")

routing_strategy = get_routing_strategy(
    strategy_name=os.environ.get("ROUTING_STRATEGY", "passthrough"),
    stall_min_tokens=int(os.environ.get("STALL_MIN_TOKENS", "20")),
    confidence_threshold=float(os.environ.get("LOCAL_CONFIDENCE_THRESHOLD", "0.8")),
)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def relay(path: str, request: Request) -> StreamingResponse:
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k != "host"}

    async with httpx.AsyncClient(timeout=120) as client:
        ollama_resp = await client.request(
            method=request.method,
            url=f"{OLLAMA_URL}/{path}",
            content=body,
            headers=headers,
        )

        try:
            resp_json = ollama_resp.json()
            should_escalate = await routing_strategy.should_escalate(
                request_body=json.loads(body) if body else {},
                local_response=resp_json,
            )
        except Exception:
            should_escalate = False

        if should_escalate and CLAUDE_KEY:
            import redis
            r = redis.from_url(os.environ.get("REDIS_URL", "redis://acorn-redis:6379"))
            r.incr("acorn:telemetry:escalations")
            claude_resp = await client.request(
                method=request.method,
                url=f"{CLAUDE_URL}/{path}",
                content=body,
                headers={**headers, "x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01"},
            )
            return StreamingResponse(
                iter([claude_resp.content]),
                status_code=claude_resp.status_code,
                media_type=claude_resp.headers.get("content-type"),
            )

    return StreamingResponse(
        iter([ollama_resp.content]),
        status_code=ollama_resp.status_code,
        media_type=ollama_resp.headers.get("content-type", "application/json"),
    )

@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "routing_strategy": os.environ.get("ROUTING_STRATEGY", "passthrough")}
```

### 5.6 acorn-api-relay strategies.py

```python
# acorn_mcp/acorn-api-relay/strategies.py
"""Routing strategy implementations. All routing decisions live here."""
__pattern__ = "Strategy"

from abc import ABC, abstractmethod

class RoutingStrategy(ABC):
    @abstractmethod
    async def should_escalate(self, request_body: dict, local_response: dict) -> bool: ...

class PassthroughStrategy(RoutingStrategy):
    async def should_escalate(self, request_body: dict, local_response: dict) -> bool:
        return False

class StallDetectionStrategy(RoutingStrategy):
    def __init__(self, min_tokens: int, stall_phrases: list[str]) -> None:
        self.min_tokens = min_tokens
        self.stall_phrases = stall_phrases

    async def should_escalate(self, request_body: dict, local_response: dict) -> bool:
        text = (local_response.get("content", [{}])[0].get("text", "")
                if isinstance(local_response.get("content"), list)
                else local_response.get("choices", [{}])[0].get("message", {}).get("content", ""))
        t = text.lower().strip()
        if not t:
            return True
        if len(t.split()) < self.min_tokens:
            return True
        return any(t.startswith(p) for p in self.stall_phrases)

class ConfidenceThresholdStrategy(RoutingStrategy):
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    async def should_escalate(self, request_body: dict, local_response: dict) -> bool:
        confidence = local_response.get("confidence", 1.0)
        return float(confidence) < self.threshold

_STALL_PHRASES = ["i cannot", "i don't know how", "i'm unable", "as an ai", "i lack the ability", "i don't have access"]

def get_routing_strategy(strategy_name: str, stall_min_tokens: int = 20, confidence_threshold: float = 0.8) -> RoutingStrategy:
    import os
    if strategy_name == "stall":
        return StallDetectionStrategy(min_tokens=stall_min_tokens, stall_phrases=_STALL_PHRASES)
    if strategy_name == "confidence":
        return ConfidenceThresholdStrategy(threshold=confidence_threshold)
    return PassthroughStrategy()
```

---

## 6. WARDEN Implementation

### 6.1 WARDEN Responsibilities

- **Every 30s:** health-check services, scan orphaned containers, sync stale problems
- **Every 5min:** cleanup-orphans.sh, prune expired research cache
- **Daily / every 10 problems:** trigger Calibration Agent if enabled

### 6.2 warden.py

```python
# docker/warden/warden.py
"""
ACORN WARDEN — self-healing infrastructure daemon.
Pure infrastructure: no LLM calls, no agent logic, no self-build.
"""
__pattern__ = "Observer"

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, UTC

import httpx
import redis.asyncio as aioredis

logger = logging.getLogger("acorn.warden")

REDIS_URL = os.environ["REDIS_URL"]
API_URL = os.environ.get("ACORN_API_URL", "http://acorn-api:8000")
STALE_THRESHOLD_SECONDS = int(os.environ.get("STALE_THRESHOLD_SECONDS", "1800"))
POLL_INTERVAL = int(os.environ.get("WARDEN_POLL_INTERVAL", "30"))
FIVE_MIN = 300
_shutdown = False

async def check_service_health(client: httpx.AsyncClient) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name, url in [
        ("api", f"{API_URL}/health"),
        ("ollama", "http://acorn-ollama:11434/api/tags"),
        ("relay", "http://acorn-api-relay:9000/health"),
    ]:
        try:
            r = await client.get(url, timeout=5)
            results[name] = r.status_code == 200
        except Exception:
            results[name] = False
    return results

async def find_orphaned_containers() -> list[str]:
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=acorn-agent", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=10,
    )
    return [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]

async def write_heartbeat(r: aioredis.Redis, status: str) -> None:
    await r.set(
        "acorn:warden:heartbeat",
        json.dumps({"status": status, "ts": datetime.now(UTC).isoformat()}),
        ex=POLL_INTERVAL * 3,
    )

async def prune_research_cache(r: aioredis.Redis) -> None:
    """Prune expired research cache entries (called every 5 min)."""
    # Delegate to API endpoint
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/internal/research/prune", timeout=10)

async def run_cleanup_orphans() -> None:
    subprocess.run(["bash", "/app/scripts/cleanup-orphans.sh"], capture_output=True, timeout=60)

async def main_loop() -> None:
    r = await aioredis.from_url(REDIS_URL)
    last_five_min = time.time()
    async with httpx.AsyncClient() as client:
        while not _shutdown:
            try:
                health = await check_service_health(client)
                unhealthy = [svc for svc, ok in health.items() if not ok]
                if unhealthy:
                    logger.warning("Unhealthy services: %s", unhealthy)
                    await r.lpush("acorn:alerts",
                                  json.dumps({"unhealthy": unhealthy, "ts": time.time()}))

                orphans = await find_orphaned_containers()
                for container in orphans:
                    logger.info("Stopping orphaned container: %s", container)
                    subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=15)

                if time.time() - last_five_min >= FIVE_MIN:
                    await prune_research_cache(r)
                    await run_cleanup_orphans()
                    last_five_min = time.time()

                await write_heartbeat(r, "ok")
            except Exception as exc:
                logger.exception("WARDEN loop error: %s", exc)
                await write_heartbeat(r, "error")

            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main_loop())
```

---

## 7. PostgreSQL Schema (Full DDL)

```sql
-- api/db/schema.sql
-- Run once on first postgres startup via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Problems ─────────────────────────────────────────────────────────────────

CREATE TABLE problems (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title            TEXT NOT NULL,
    description      TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','assembling','active','validating','complete','failed')),
    problem_class    TEXT,
    input_manifest   JSONB,
    output_format    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    worktree_path    TEXT
);

-- ─── Tasks ────────────────────────────────────────────────────────────────────

CREATE TABLE tasks (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id     UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    task_type      TEXT NOT NULL
                   CHECK (task_type IN ('research','synthesise','domain-analyse','validate','deliver','kernel-extract')),
    title          TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','claimed','complete','failed')),
    assigned_agent TEXT,
    claimed_at     TIMESTAMPTZ,
    completed_at   TIMESTAMPTZ,
    result         JSONB,
    reasoning_steps INT DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON tasks (problem_id, status);

-- ─── Mailbox ──────────────────────────────────────────────────────────────────

CREATE TABLE mailbox (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id   UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    from_agent   TEXT NOT NULL,
    to_agent     TEXT,
    message_type TEXT NOT NULL,
    payload      JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at      TIMESTAMPTZ
);

CREATE INDEX ON mailbox (problem_id, to_agent);

-- ─── Episodic Memory ──────────────────────────────────────────────────────────

CREATE TABLE episodes (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id       UUID REFERENCES problems(id) ON DELETE SET NULL,
    agent_id         TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    payload          JSONB NOT NULL DEFAULT '{}',
    embedding        vector(768),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON episodes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON episodes (agent_id, created_at DESC);

-- ─── Kernels ───────────────────────────────────────────────────────────────────

CREATE TABLE kernels (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name             TEXT NOT NULL UNIQUE,
    version          TEXT NOT NULL DEFAULT '1.0.0',
    category         TEXT NOT NULL
                     CHECK (category IN ('research','synthesis','domain','validation','code','workflow','general')),
    status           TEXT NOT NULL DEFAULT 'probationary'
                     CHECK (status IN ('probationary','permanent','deprecated')),
    description      TEXT NOT NULL,
    trigger_keywords TEXT[] NOT NULL DEFAULT '{}',
    implementation   TEXT,
    test_suite       TEXT,
    benchmark        JSONB,
    use_count        INT NOT NULL DEFAULT 0,
    embedding        vector(768),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    promoted_at      TIMESTAMPTZ,
    deprecated_at    TIMESTAMPTZ
);

CREATE INDEX ON kernels USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON kernels (status, category);
CREATE INDEX ON kernels USING gin (trigger_keywords);

-- ─── Reasoning Steps ──────────────────────────────────────────────────────────

CREATE TABLE reasoning_steps (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id   UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    agent_id     TEXT NOT NULL,
    step_type    TEXT NOT NULL,
    summary      TEXT NOT NULL,
    confidence   FLOAT,
    sources      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON reasoning_steps (problem_id, created_at);

-- ─── Research Cache ───────────────────────────────────────────────────────────

CREATE TABLE research_cache (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_hash    TEXT NOT NULL UNIQUE,
    query_text    TEXT NOT NULL,
    results       JSONB NOT NULL DEFAULT '{}',
    source_urls   TEXT[] DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ
);

CREATE INDEX ON research_cache (query_hash);

-- ─── Agent Telemetry ──────────────────────────────────────────────────────────

CREATE TABLE agent_telemetry (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id       TEXT NOT NULL,
    problem_id     UUID REFERENCES problems(id) ON DELETE SET NULL,
    tool_name      TEXT NOT NULL,
    duration_ms    INT,
    model_used     TEXT,
    tokens_in      INT,
    tokens_out     INT,
    success        BOOLEAN NOT NULL DEFAULT TRUE,
    error_msg      TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON agent_telemetry (problem_id, agent_id);
CREATE INDEX ON agent_telemetry (created_at DESC);

-- ─── Judge Verdicts ───────────────────────────────────────────────────────────

CREATE TABLE judge_verdicts (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id   UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    task_id      UUID REFERENCES tasks(id) ON DELETE SET NULL,
    agent_id     TEXT NOT NULL,
    verdict      TEXT NOT NULL CHECK (verdict IN ('pass','fail')),
    checks       JSONB NOT NULL DEFAULT '{}',
    reasoning    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON judge_verdicts (problem_id, created_at);
```

---

## 8. Docker Compose

### 8.1 Base (docker/docker-compose.yml)

```yaml
name: acorn
version: "3.9"

x-acorn-common: &acorn-common
  restart: unless-stopped
  networks: [acorn-net]
  env_file: [.env]

services:
  acorn-postgres:
    <<: *acorn-common
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: acorn
      POSTGRES_PASSWORD: acorn
      POSTGRES_DB: acorn
    volumes:
      - acorn-pgdata:/var/lib/postgresql/data
      - ./api/db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U acorn -d acorn"]
      interval: 10s
      timeout: 5s
      retries: 5

  acorn-redis:
    <<: *acorn-common
    image: redis:7-alpine
    volumes: [acorn-redisdata:/data]
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  acorn-ollama:
    <<: *acorn-common
    image: ollama/ollama:latest
    volumes: [acorn-ollamadata:/root/.ollama]
    ports: ["11434:11434"]
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:11434/api/tags || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  acorn-api-relay:
    <<: *acorn-common
    build: ./acorn_mcp/acorn-api-relay
    ports: ["9000:9000"]
    environment:
      OLLAMA_BASE_URL: http://acorn-ollama:11434
      REDIS_URL: redis://acorn-redis:6379
    depends_on:
      acorn-ollama: {condition: service_healthy}
      acorn-redis: {condition: service_healthy}

  acorn-api:
    <<: *acorn-common
    build: ./api
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://acorn:acorn@acorn-postgres:5432/acorn
      REDIS_URL: redis://acorn-redis:6379
      OLLAMA_BASE_URL: http://acorn-ollama:11434
    depends_on:
      acorn-postgres: {condition: service_healthy}
      acorn-redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5

  acorn-ui:
    <<: *acorn-common
    build: ./ui-next
    ports: ["8501:8501"]
    environment:
      ACORN_API_URL: http://acorn-api:8000
    depends_on:
      acorn-api: {condition: service_healthy}

  acorn-warden:
    <<: *acorn-common
    build: ./docker/warden
    environment:
      REDIS_URL: redis://acorn-redis:6379
      ACORN_API_URL: http://acorn-api:8000
    depends_on:
      acorn-api: {condition: service_healthy}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

volumes:
  acorn-pgdata:
  acorn-redisdata:
  acorn-ollamadata:
  acorn-workspaces:

networks:
  acorn-net:
    driver: bridge
```

### 8.2 DGX Spark Profile (docker/docker-compose.dgx.yml)

```yaml
# PRIMARY platform. NVIDIA GPU. Up to 5 concurrent problems.
include: [docker-compose.yml]

services:
  acorn-ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      ACORN_MODE: dgx
      NVIDIA_VISIBLE_DEVICES: all

  acorn-api:
    environment:
      ACORN_MODE: dgx
      DEFAULT_MODEL: qwen3-coder
      SYNTHESIS_MODEL: qwen3-coder
      RESEARCH_MODEL: qwen2.5:14b
      MAX_AGENTS_PER_PROBLEM: "10"
      MAX_CONCURRENT_PROBLEMS: "5"
      MAX_HARNESS_CONTAINERS: "20"
      ROUTING_STRATEGY: passthrough
```

### 8.3 Mac Mini M4 Profile (docker/docker-compose.mini.yml)

```yaml
# Metal backend. Up to 2 concurrent problems.
include: [docker-compose.yml]

services:
  acorn-ollama:
    environment:
      ACORN_MODE: mini
      OLLAMA_METAL: "1"

  acorn-api:
    environment:
      ACORN_MODE: mini
      DEFAULT_MODEL: qwen3-coder
      SYNTHESIS_MODEL: qwen2.5:14b
      RESEARCH_MODEL: qwen2.5:14b
      MAX_AGENTS_PER_PROBLEM: "4"
      MAX_CONCURRENT_PROBLEMS: "2"
      MAX_HARNESS_CONTAINERS: "8"
      ROUTING_STRATEGY: confidence
      LOCAL_CONFIDENCE_THRESHOLD: "0.72"
```

### 8.4 Cloud GPU Profile (docker/docker-compose.cloud.yml)

```yaml
# vLLM replaces Ollama. Up to 10 concurrent.
include: [docker-compose.yml]

services:
  acorn-ollama:
    image: vllm/vllm-openai:latest
    command: ["--model", "Qwen/Qwen2.5-14B-Instruct", "--served-model-name", "qwen2.5:14b", "--port", "11434"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  acorn-api:
    environment:
      ACORN_MODE: cloud
      MAX_AGENTS_PER_PROBLEM: "15"
      MAX_CONCURRENT_PROBLEMS: "10"
      MAX_HARNESS_CONTAINERS: "40"
      ROUTING_STRATEGY: stall
      STALL_DETECTION_ENABLED: "true"
```

---

## 9. Hardware Profiles

| Platform | Compose file | Default models | Notes |
|----------|--------------|---------------|-------|
| DGX Spark | docker-compose.dgx.yml | qwen3-coder, qwen2.5:14b, llama3.3:70b | **PRIMARY.** NVIDIA GPU. Up to 5 concurrent problems. |
| Mac Mini M4 | docker-compose.mini.yml | qwen3-coder, qwen2.5:14b | Metal backend. Up to 2 concurrent problems. |
| Cloud GPU | docker-compose.cloud.yml | qwen3-coder, qwen2.5:14b | vLLM replaces Ollama. Up to 10 concurrent. |

---

## 10. Scripts

### 10.1 bootstrap.sh

```bash
#!/bin/bash
# scripts/bootstrap.sh
# Full ACORN setup — run once on a fresh machine.
# Usage: bash scripts/bootstrap.sh [dgx|mini|cloud]
# Default: dgx (PRIMARY)

set -euo pipefail

MODE="${1:-dgx}"
echo "═══════════════════════════════════════════════════"
echo "  ACORN Bootstrap — mode: ${MODE}"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "═══════════════════════════════════════════════════"

# Clone if not present
if [ ! -d "acorn" ]; then
  git clone https://github.com/SharathSPhD/acorn.git acorn
fi
cd acorn

# Create branch structure
git checkout -b acorn/agents 2>/dev/null || true
git checkout -b acorn/kernels 2>/dev/null || true
git checkout -b acorn/ui 2>/dev/null || true
git checkout main

# Create workspace directories and worktrees
mkdir -p acorn-workspaces
git worktree add acorn-workspaces/agents acorn/agents 2>/dev/null || true
git worktree add acorn-workspaces/kernels acorn/kernels 2>/dev/null || true
git worktree add acorn-workspaces/ui acorn/ui 2>/dev/null || true

# Kernel grove structure
mkdir -p acorn-workspaces/kernels/{permanent,probationary,deprecated}
touch acorn-workspaces/kernels/permanent/.gitkeep
touch acorn-workspaces/kernels/probationary/.gitkeep
touch acorn-workspaces/kernels/deprecated/.gitkeep

# Research cache
mkdir -p acorn-workspaces/research-cache
touch acorn-workspaces/research-cache/.gitkeep

# Configure environment
cp .env.example .env 2>/dev/null || true
[ -f ".env.${MODE}" ] && cat ".env.${MODE}" >> .env

# Build images
echo "─── Building acorn-api-relay ───"
docker build -t acorn-api-relay:latest ./acorn_mcp/acorn-api-relay

echo "─── Building acorn-harness ───"
docker build -t acorn-harness:latest ./docker/acorn-harness

echo "─── Building acorn-warden ───"
docker build -t acorn-warden:latest ./docker/warden

# Start stack
COMPOSE_FILE="docker/docker-compose.${MODE}.yml"
docker compose -f "${COMPOSE_FILE}" up -d \
  acorn-postgres acorn-redis acorn-ollama \
  acorn-api-relay acorn-api acorn-ui acorn-warden

echo "Waiting for services..."
sleep 20

# Verify schema
docker exec acorn-postgres psql -U acorn -d acorn -c "\dt" | grep -c "table" \
  && echo "✓ Schema verified" || echo "✗ Schema check failed"

# Pull models (DGX)
if [ "${MODE}" = "dgx" ]; then
  docker exec acorn-ollama ollama pull qwen3-coder
  docker exec acorn-ollama ollama pull qwen2.5:14b
  docker exec acorn-ollama ollama pull llama3.3:70b
  docker exec acorn-ollama ollama pull nomic-embed-text
elif [ "${MODE}" = "mini" ]; then
  docker exec acorn-ollama ollama pull qwen3-coder
  docker exec acorn-ollama ollama pull qwen2.5:14b
  docker exec acorn-ollama ollama pull nomic-embed-text
fi

# Verify relay
curl -sf -H "Authorization: Bearer ollama" http://localhost:9000/v1/models \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ Relay OK')" \
  || echo "✗ Relay check failed"

# Verify API
curl -sf http://localhost:8000/health | python3 -c "import sys,json; print('✓ API OK')" || echo "✗ API failed"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ACORN Bootstrap Complete"
echo "  Hub UI: http://localhost:8501"
echo "  API:    http://localhost:8000"
echo "  Relay:  http://localhost:9000"
echo "  To start a problem: bash scripts/new-problem.sh"
echo "═══════════════════════════════════════════════════"
```

### 10.2 new-problem.sh

```bash
#!/bin/bash
# scripts/new-problem.sh
# Creates isolated git worktree and launches Orchestrator agent.

set -euo pipefail

PROBLEM_UUID="${1:-$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -c1-8)}"
BRANCH="acorn/problem-${PROBLEM_UUID}"
WORKSPACE="${PWD}/acorn-workspaces/problem-${PROBLEM_UUID}"

cd acorn

# Create isolated git worktree
git worktree add "${WORKSPACE}" -b "${BRANCH}" 2>/dev/null || git worktree add "${WORKSPACE}" "${BRANCH}"

# Write problem manifest stub
cat > "${WORKSPACE}/PROBLEM.md" << EOF
# Problem ${PROBLEM_UUID}

**Status:** pending
**Created:** $(date -u '+%Y-%m-%dT%H:%M:%SZ')

## Description
Agent will populate after reading problem submission from TRUNK API.

## Input Manifest
Agent will populate after reading input artefacts.

## Output Format
Agent will populate after Orchestrator decomposition.

## Constraints
- All sources must be cited in RESEARCH.md
- All uncertainty must be flagged with [UNCERTAIN]
- REASONING_TRAIL.md must be written before Judge invocation
EOF

# Create task coordination folder
mkdir -p "${WORKSPACE}/.claude/tasks/acorn-${PROBLEM_UUID}"
echo '{"problem_id":"'${PROBLEM_UUID}'","tasks":{},"kernels_applied":[],"last_updated":"'$(date -u '+%Y-%m-%dT%H:%M:%SZ')'"}' \
  > "${WORKSPACE}/.claude/tasks/acorn-${PROBLEM_UUID}/status.json"

# Insert problem into PostgreSQL via API
curl -sf -X POST "http://localhost:8000/api/problems" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Problem ${PROBLEM_UUID}\",\"description\":\"Pending\",\"id\":\"${PROBLEM_UUID}\",\"worktree_path\":\"${WORKSPACE}\"}" \
  || true

echo "Problem workspace ready: ${WORKSPACE}"
echo "Branch: ${BRANCH}"
echo "Launching Orchestrator..."

docker run --rm \
  --network acorn_acorn-net \
  --name "acorn-agent-${PROBLEM_UUID}-orchestrator" \
  -e ACORN_AGENT_ID=orchestrator \
  -e ACORN_PROBLEM_UUID="${PROBLEM_UUID}" \
  -e REDIS_URL=redis://acorn-redis:6379 \
  -e DATABASE_URL=postgresql://acorn:acorn@acorn-postgres:5432/acorn \
  -e ANTHROPIC_BASE_URL=http://acorn-api-relay:9000 \
  -e ANTHROPIC_AUTH_TOKEN=ollama \
  -e ANTHROPIC_API_KEY= \
  -e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 \
  -v acorn_acorn-workspaces:/acorn-workspaces \
  -v "${PWD}/.claude:/root/.claude:ro" \
  acorn-harness:latest
```

### 10.3 cleanup-orphans.sh

```bash
#!/bin/bash
# scripts/cleanup-orphans.sh
# Stops harness containers with no matching active task.

set -euo pipefail

for name in $(docker ps --filter "name=acorn-agent" --format "{{.Names}}" 2>/dev/null); do
  # Check if problem/task still active in DB; if not, stop container
  uuid=$(echo "$name" | sed -n 's/acorn-agent-\([^-]*\)-.*/\1/p')
  if [ -n "$uuid" ]; then
    status=$(curl -sf "http://localhost:8000/api/problems/${uuid}" 2>/dev/null | jq -r '.status // "unknown"')
    if [ "$status" = "complete" ] || [ "$status" = "failed" ] || [ "$status" = "unknown" ]; then
      echo "Stopping orphan: $name"
      docker rm -f "$name" 2>/dev/null || true
    fi
  fi
done
```

---

## 11. Next.js Hub (CANOPY)

### 11.1 Hub Pages

| Page | Path | Purpose |
|------|------|---------|
| Submit | `/submit` | Problem submission: title, description, input artefacts, output format |
| Status | `/status/[id]` | Live status: task list, agent activity feed via WebSocket, kernel retrievals, reasoning steps |
| Gallery | `/gallery` | Completed problems: filters, links to outputs and reasoning trails |
| Kernel Library | `/kernels` | Kernel grove browser: search, promote probationary, benchmark history |
| Telemetry | `/telemetry` | Agent metrics: tokens, duration, escalation rate, WARDEN health |
| Reasoning Trails | `/reasoning/[id]` | Full trail viewer: step-by-step decisions, kernel retrievals, judge verdicts |

### 11.2 Hub Design Constraints

- **No agent logic in Hub code.** Any computation beyond API call + render is a violation.
- **WebSocket reconnect.** Status page must implement exponential-backoff reconnect (max 5 attempts).
- **Sensitive data.** Problem descriptions never displayed raw in gallery — only titles, statuses, aggregated metrics.

---

## 12. Exit Criteria (v1.0 Release)

All of the following must be true for v1.0 release. **No phases** — everything is built in one release.

1. **Schema:** All 9 schema tables created with correct constraints (problems, tasks, mailbox, episodes, kernels, reasoning_steps, research_cache, agent_telemetry, judge_verdicts).

2. **TRUNK API:** All 7 routers operational with OpenAPI docs: problems, agents, tasks, kernels, telemetry, research, reasoning, mailbox.

3. **acorn-harness:** Container builds and runs with tool-proxy, session state, deny-patterns.

4. **acorn-api-relay:** Routes to Ollama correctly; escalation path works when key provided.

5. **Full agent team pipeline:** research → synthesise → validate → judge PASS.

6. **REASONING_TRAIL.md:** Written with all step types (decomposition, kernel_retrieval, research_strategy, synthesis_approach, uncertainty_flag, validation_outcome, judge_verdict).

7. **Kernel Extractor:** Produces KERNEL.md in probationary grove after PASS.

8. **Kernel promotion:** Works after 2 independent verified uses.

9. **WARDEN:** Health checks, orphan cleanup, stale problem sync all operational.

10. **Next.js Hub:** Submit, status, gallery, kernel library, telemetry, reasoning trails pages.

11. **WebSocket:** Live streaming from agent events to Hub.

12. **CI:** ruff, mypy, pytest (unit + contract) all pass.

13. **Profiles:** DGX Spark fully operational; Mini and Cloud profiles build without error.

14. **bootstrap.sh:** Runs end-to-end on a fresh DGX Spark.

---

## 13. Environment Variables (.env.example)

```bash
# ACORN_MODE — dgx | mini | cloud
ACORN_MODE=dgx

# Relay recipe
ANTHROPIC_BASE_URL=http://acorn-api-relay:9000
ANTHROPIC_AUTH_TOKEN=ollama
ANTHROPIC_API_KEY=
ANTHROPIC_API_KEY_REAL=

# Database and cache
DATABASE_URL=postgresql://acorn:acorn@acorn-postgres:5432/acorn
REDIS_URL=redis://acorn-redis:6379

# Model routing
DEFAULT_MODEL=qwen3-coder
SYNTHESIS_MODEL=qwen3-coder
RESEARCH_MODEL=qwen2.5:14b

# Routing
ROUTING_STRATEGY=passthrough
STALL_DETECTION_ENABLED=false
STALL_MIN_TOKENS=20
LOCAL_CONFIDENCE_THRESHOLD=0.8

# Resource caps
MAX_AGENTS_PER_PROBLEM=10
MAX_CONCURRENT_PROBLEMS=5
MAX_HARNESS_CONTAINERS=20

# Session and memory
ACORN_SESSION_TTL_HOURS=24
ACORN_IDLE_TIMEOUT_SECONDS=120

# Kernel grove
ACORN_KERNEL_PROMO_THRESHOLD=2
KERNEL_DEPRECATION_THRESHOLD=0.4
```

---

*End of spec.md v1.0*
