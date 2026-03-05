# ACORN — Product Requirements Document

**Adaptive Collaborative Orchestration and Reasoning Network**

Version: 1.0 · March 2026

ACORN is a self-evolving autonomous knowledge-work factory. It accepts raw inputs — goals, documents, datasets, URLs — and produces knowledge artefacts: reports, recommendations, synthesised summaries, BI dashboards, workflow scripts, and deployed apps.

---

## 1. Implementation Rules

### 1.1 Design Patterns First

Every production module **MUST** declare `__pattern__` at module level before any other code:

```python
__pattern__ = "Repository"  # or Factory, Strategy, Observer, etc.
```

The `conftest.py` fixture fails test collection for any production module missing this attribute.

**Declared patterns:** Factory, Strategy, Observer, ChainOfResponsibility, Repository, StateMachine, TemplateMethod, Decorator, EventDriven

### 1.2 Test-Driven Development (strict)

Red → Green → Refactor. No production code before a failing test. PRs rejected if production code lacks tests.

**Test naming:** `test_{unit}__{condition}__{expected_outcome}`

### 1.3 Configuration-Driven

`api/config.py` is the **ONLY** file that reads `os.environ`. All other code imports `from api.config import settings`. Direct `os.environ` access elsewhere is a ruff violation and CI blocker.

All configuration in `AcornSettings` (Pydantic BaseSettings). Adding a new platform never requires code change — only a new `.env.{profile}`.

**Key settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ACORN_MODE` | `dgx` | Platform: `dgx` \| `mini` \| `cloud` |
| `ACORN_API_URL` | `http://acorn-api:8000` | TRUNK API base URL |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | — | Redis connection string |
| `MAX_AGENTS_PER_PROBLEM` | `8` | Max agents per problem |
| `MAX_CONCURRENT_PROBLEMS` | `3` (DGX), `1` (mini), `5` (cloud) | Concurrent problems |
| `MAX_HARNESS_CONTAINERS` | `15` | Max harness containers |
| `ACORN_KERNEL_PROMO_THRESHOLD` | `2` | Independent problems for kernel promotion |
| `KERNEL_DEPRECATION_THRESHOLD` | `0.4` | Pass rate below which kernel is deprecated |
| `CALIBRATION_AGENT_ENABLED` | `false` | Enable Calibration Agent |
| `INTERFACE_AGENT_ENABLED` | `false` | Enable Interface Agent |
| `ACORN_IDLE_TIMEOUT_SECONDS` | `120` | Idle threshold for re-focus injection |
| `ACORN_SESSION_TTL_HOURS` | `24` | Redis session TTL |
| `ORCHESTRATOR_MODEL` | — | Override orchestrator model |
| `RESEARCH_MODEL` | — | Override research analyst model |
| `SYNTHESIS_MODEL` | — | Override synthesis agent model |
| `JUDGE_MODEL` | — | Override judge model |

### 1.4 Hooks Are Thin Relays

Each `.claude/hooks/*.sh` script does exactly one thing: POST a serialised `AgentEvent` to `http://acorn-api:8000/internal/events`. All business logic in Python `EventSubscriber` classes. >10 lines of logic = violation.

### 1.5 Kernel Promotion Is Gated

Kernels write to `kernels/probationary/` only. Promotion to `permanent/` goes through `KernelRepository.promote()`, enforcing `ACORN_KERNEL_PROMO_THRESHOLD` (default: 2 independent problems). Never write directly to `permanent/`.

### 1.6 Anti-Patterns (forbidden)

- **God Orchestrator:** Orchestrator only decomposes and spawns. State transitions, events, kernel promotion belong in their respective components.
- **Inline routing conditionals:** All routing decisions in a named `RoutingStrategy` subclass.
- **Direct os.environ access** outside `api/config.py`
- **Fat hooks:** hooks call the API; Python classes do the work
- **Probationary kernel bypass:** no direct writes to `permanent/`
- **Reasoning trail omission:** no Judge verdict without `REASONING_TRAIL.md`

---

## 2. Architecture Layers

| Layer | Component | Port |
|-------|-----------|------|
| **CANOPY** | Next.js Hub UI | 8501 |
| **TRUNK** | FastAPI API Gateway | 8000 |
| **GROVE** | Agent Engine (acorn-harness containers) | — |
| **RELAY** | acorn-api-relay | 9000 |
| **WARDEN** | Self-healing daemon (no LLM) | — |
| **ROOTS** | PostgreSQL 16 + pgvector, Redis 7 | 5432, 6379 |
| **SOIL** | DGX Spark / Mac Mini M4 / Cloud GPU | — |

**Hard rule:** TRUNK and below own all computation and data. CANOPY is a thin REST/WebSocket consumer.

---

## 3. Agent Model

Every agent session runs inside an `acorn-harness` container. Claude Code is pointed at `acorn-api-relay` via:

```bash
ANTHROPIC_BASE_URL=http://acorn-api-relay:9000
ANTHROPIC_AUTH_TOKEN=ollama
ANTHROPIC_API_KEY=  # Intentionally empty; relay manages escalation
```

---

## 4. Kernel Architecture

Kernels replace OAK's skills. Each kernel contains:

- **KERNEL.md** — description, prerequisites, composition, known edge cases
- **Python module** — executable, type-annotated, with `__pattern__`
- **Test suite** — pytest, no external deps
- **Benchmark results**

**Lifecycle:** probationary → permanent → deprecated (never deleted)

---

## 5. Reasoning Trail Architecture

Every problem produces `REASONING_TRAIL.md` containing:

- Decomposition decisions by Orchestrator
- Kernel retrieval decisions
- Research strategy choices
- Synthesis approach selections
- Uncertainty flags
- Validation outcomes
- Judge verdict chain

---

## 6. WARDEN (Infrastructure Daemon)

Pure infrastructure. No LLM access. No reasoning.

- Health checks every 30s
- Orphan container cleanup
- Stale problem detection
- Kernel benchmark index updates
- Calibration Agent triggers (if enabled)

---

## 7. Security Model

- Docker network isolation (`acorn-net`)
- No OpenClaw components
- No third-party messaging (Slack, email, WhatsApp)
- Single trusted operator on private network
- Two-layer deny-list (`tool-proxy.sh` + `pre-tool-use.sh` hook)
- Agent capability sets (tools listed in agent definition)
- Reasoning trails as audit mechanism

---

## 8. Environment Variables Reference

| Variable | Default | Description | Profile Override |
|----------|---------|-------------|------------------|
| `ACORN_MODE` | `dgx` | Platform: dgx \| mini \| cloud | All |
| `ACORN_API_URL` | `http://acorn-api:8000` | TRUNK API base | All |
| `DATABASE_URL` | `postgresql://acorn:acorn@acorn-postgres:5432/acorn` | PostgreSQL | All |
| `REDIS_URL` | `redis://acorn-redis:6379` | Redis | All |
| `MAX_AGENTS_PER_PROBLEM` | `8` | Max agents per problem | dgx: 10, mini: 4, cloud: 15 |
| `MAX_CONCURRENT_PROBLEMS` | `3` | Concurrent problems | dgx: 5, mini: 1, cloud: 5 |
| `MAX_HARNESS_CONTAINERS` | `15` | Max harness containers | dgx: 20, mini: 8, cloud: 40 |
| `ACORN_KERNEL_PROMO_THRESHOLD` | `2` | Problems for kernel promotion | — |
| `KERNEL_DEPRECATION_THRESHOLD` | `0.4` | Pass rate for deprecation | — |
| `CALIBRATION_AGENT_ENABLED` | `false` | Enable Calibration Agent | — |
| `INTERFACE_AGENT_ENABLED` | `false` | Enable Interface Agent | — |
| `ACORN_IDLE_TIMEOUT_SECONDS` | `120` | Idle timeout for re-focus | — |
| `ACORN_SESSION_TTL_HOURS` | `24` | Session TTL in Redis | — |
| `ORCHESTRATOR_MODEL` | — | Orchestrator model override | — |
| `RESEARCH_MODEL` | — | Research analyst model override | — |
| `SYNTHESIS_MODEL` | — | Synthesis agent model override | — |
| `JUDGE_MODEL` | — | Judge model override | — |
| `ANTHROPIC_BASE_URL` | `http://acorn-api-relay:9000` | Relay URL (harness) | — |
| `ANTHROPIC_AUTH_TOKEN` | `ollama` | Auth token for relay | — |
| `ANTHROPIC_API_KEY` | (empty) | Intentionally empty | — |
| `ANTHROPIC_API_KEY_REAL` | (empty) | Real key for escalation | — |
| `ROUTING_STRATEGY` | `passthrough` | passthrough \| stall \| confidence | — |
| `STALL_DETECTION_ENABLED` | `false` | Enable stall-based escalation | — |
| `STALL_MIN_TOKENS` | `20` | Min tokens before stall | — |
| `LOCAL_CONFIDENCE_THRESHOLD` | `0.8` | Confidence for escalation | — |
| `OLLAMA_BASE_URL` | `http://acorn-ollama:11434` | Ollama endpoint | — |
| `KERNEL_PROBATIONARY_PATH` | `/acorn-workspaces/kernels/probationary` | Probationary path | — |
| `KERNEL_PERMANENT_PATH` | `/acorn-workspaces/kernels/permanent` | Permanent path | — |
| `WARDEN_POLL_INTERVAL` | `30` | WARDEN health check interval (s) | — |
| `STALE_THRESHOLD_SECONDS` | `1800` | Stale problem threshold | — |

---

## 9. Commit Message Format

```
type(scope): subject

body (optional)

Refs: #issue_number
```

**Types:** feat, fix, test, refactor, chore, docs

**Scopes:** trunk, grove, harness, relay, memory, canopy, kernels, config, warden

---

## 10. PostgreSQL Schema Tables

| Table | Key Columns |
|-------|-------------|
| **problems** | id, title, description, problem_class, status, input_manifest, output_manifest, solution_url, reasoning_trail, kernels_used, created_at, completed_at |
| **tasks** | id, problem_id, type, title, description, status, assigned_to, depends_on, created_at, claimed_at, completed_at |
| **mailbox** | id, problem_id, from_agent, to_agent, subject, body, read, created_at |
| **episodes** | id, problem_id, agent_id, event_type, content, importance, embedding (vector), retrieved_count, last_retrieved_at, archived_at, created_at |
| **kernels** | id, name, version, category, description, trigger_keywords, embedding (vector), status, filesystem_path, module_path, test_path, verified_on_problems, use_count, pass_rate, median_execution_ms, last_benchmark_at, promoted_at, deprecated_at, deprecated_reason, created_at, updated_at |
| **reasoning_steps** | id, problem_id, task_id, agent_id, step_type, summary, detail, confidence, created_at |
| **research_cache** | id, query_hash, query_text, sources, embedding (vector), hit_count, created_at, expires_at |
| **agent_telemetry** | id, problem_id, agent_id, tool_name, duration_ms, success, error_msg, model_used, tokens_in, tokens_out, escalated, kernel_used, created_at |
| **judge_verdicts** | id, task_id, problem_id, verdict, checks, failing_agent, notes, created_at |
