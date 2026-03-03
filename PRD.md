# OAK — Product Requirements Document
## Version 1.0 · March 2026

> **Relationship to spec.md:** This document is the engineering companion to `spec.md`. Where the spec defines *what* OAK is and *what* it must achieve, this PRD defines *how* it must be built: the design patterns governing each subsystem, the TDD workflow that gates every phase, and the configuration model that makes the system platform- and operator-portable. Do not duplicate spec content here; reference it by section number.

---

## 1. Purpose and Scope

This PRD governs all implementation decisions for OAK from Phase 0 (walking skeleton) through Phase 5 (concurrent cloud deployment), as defined in spec §14. It applies to every engineer and agent contributing code to the `main`, `oak/agents`, `oak/skills`, and `oak/ui` branches.

Three engineering mandates govern every component in OAK:

1. **Design patterns first.** Every subsystem must map to one or more named design patterns before a line of code is written. Patterns are not decorative — they are the mechanism by which components stay replaceable and independently testable.

2. **Test-Driven Development.** No production code is written before a failing test describes its required behaviour. The test suite is the system specification in executable form.

3. **Configuration-driven.** No behaviour is hardcoded. Every tunable, every threshold, every platform difference is controlled by a configuration value with a validated default. Adding a new platform target must never require a code change.

---

## 2. Design Pattern Registry

Every OAK component belongs to one or more of the patterns below. When a new component is designed, the engineer must declare which pattern(s) it implements in a docstring before implementation begins. This is enforced by a `conftest.py` fixture that fails any test file that imports a module without a `__pattern__` module-level attribute.

### 2.1 Factory — Agent and Problem Assembly

**Where used:** `api/routers/problems.py`, `api/routers/agents.py`, `.claude/agents/`.

**What it solves:** The agent set for any given problem is not known at startup. It is determined at runtime by the Orchestrator reading the problem manifest. The Factory pattern decouples the creation logic from the consumer, keeping the Orchestrator's decomposition code free of `if problem_type == "timeseries": spawn(MLEngineer)` conditionals.

**Implementation contract:**

```python
# api/factories/agent_factory.py
__pattern__ = "Factory"

from abc import ABC, abstractmethod
from typing import Protocol

class AgentSpec(Protocol):
    agent_id: str
    role: str
    harness_image: str
    resource_limits: dict

class AgentFactory(ABC):
    """Abstract factory for agent session creation.
    Each platform profile provides a concrete subclass."""

    @abstractmethod
    def create(self, role: str, problem_uuid: str) -> AgentSpec:
        """Produce an agent spec; does not launch the container."""
        ...

    @abstractmethod
    def launch(self, spec: AgentSpec) -> str:
        """Launch the harness container; return container ID."""
        ...

class DGXAgentFactory(AgentFactory):
    """Concrete factory for DGX Spark profile.
    GPU passthrough, full 70B model set, high MAX_AGENTS."""
    ...

class MiniAgentFactory(AgentFactory):
    """Concrete factory for Mac Mini M4 profile.
    Metal backend, smaller models, conservative resource limits."""
    ...

class CloudAgentFactory(AgentFactory):
    """Concrete factory for cloud GPU profile.
    vLLM backend, Kubernetes job creation, horizontal scaling."""
    ...
```

**TDD note:** The factory is tested with a `MockAgentFactory` that returns deterministic `AgentSpec` objects without touching Docker. Production factories are integration-tested against a running Docker daemon in Phase 1 CI only.

---

### 2.2 Strategy — Inference Routing

**Where used:** `oak_mcp/oak-api-proxy/main.py`.

**What it solves:** The routing logic inside `oak-api-proxy` (local Ollama vs Claude API escalation) must be swappable without restructuring the proxy. Stall detection heuristics are pluggable strategies, not baked-in conditionals.

**Implementation contract:**

```python
# oak_mcp/oak-api-proxy/strategies.py
__pattern__ = "Strategy"

from abc import ABC, abstractmethod

class RoutingStrategy(ABC):
    """Decides, given a request and a local response, which backend to use."""

    @abstractmethod
    async def should_escalate(self, request_body: dict, local_response: dict) -> bool:
        """Return True to escalate to Claude API; False to use local response."""
        ...

class PassthroughStrategy(RoutingStrategy):
    """Always returns False. Default in v1 — no escalation, fully local."""
    async def should_escalate(self, request_body, local_response) -> bool:
        return False

class StallDetectionStrategy(RoutingStrategy):
    """Escalates on empty, too-short, or phrase-triggered responses.
    Enabled only when STALL_DETECTION_ENABLED=true."""
    def __init__(self, min_tokens: int, stall_phrases: list[str]):
        self.min_tokens = min_tokens
        self.stall_phrases = stall_phrases

    async def should_escalate(self, request_body, local_response) -> bool:
        text = local_response.get("content", [{}])[0].get("text", "").lower().strip()
        if not text:
            return True
        if len(text.split()) < self.min_tokens:
            return True
        return any(text.startswith(p) for p in self.stall_phrases)

class ConfidenceThresholdStrategy(RoutingStrategy):
    """Escalates when the model's self-reported confidence field drops below threshold.
    Used in mini profile where local model capability is more limited."""
    def __init__(self, threshold: float):
        self.threshold = threshold

    async def should_escalate(self, request_body, local_response) -> bool:
        confidence = local_response.get("confidence", 1.0)
        return confidence < self.threshold
```

**Configuration binding:**

```python
# Loaded from config at proxy startup — no code change required to switch strategy.
ROUTING_STRATEGY = {
    "passthrough":   PassthroughStrategy,
    "stall":         StallDetectionStrategy,
    "confidence":    ConfidenceThresholdStrategy,
}[settings.routing_strategy]
```

---

### 2.3 Observer — Telemetry and Hooks

**Where used:** `.claude/hooks/`, `api/ws/stream.py`, `memory/episodic.py`.

**What it solves:** Multiple consumers need to react to the same agent event (a tool call completes → update telemetry, update session state, publish to WebSocket stream). Adding a new consumer must not require modifying the event source. The Observer pattern decouples producers from consumers entirely.

**Implementation contract:**

```python
# api/events/bus.py
__pattern__ = "Observer"

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class AgentEvent:
    event_type: str          # tool_called | task_claimed | task_complete | judge_verdict | agent_spawned
    agent_id: str
    problem_uuid: str
    payload: dict[str, Any]
    timestamp_utc: float

class EventSubscriber(ABC):
    @abstractmethod
    async def on_event(self, event: AgentEvent) -> None: ...

class TelemetrySubscriber(EventSubscriber):
    """Writes to agent_telemetry table on every tool_called event."""
    ...

class WebSocketSubscriber(EventSubscriber):
    """Publishes to Redis pub/sub channel oak:stream:{problem_uuid}."""
    ...

class EpisodicMemorySubscriber(EventSubscriber):
    """Writes significant events to episodes table with embedding."""
    ...

class SessionStateSubscriber(EventSubscriber):
    """Updates oak:session:{agent_id} keys in Redis after tool calls."""
    ...

class EventBus:
    """Synchronous publish; async subscribers fire concurrently via asyncio.gather."""
    _subscribers: list[EventSubscriber] = []

    def subscribe(self, subscriber: EventSubscriber) -> None:
        self._subscribers.append(subscriber)

    async def publish(self, event: AgentEvent) -> None:
        await asyncio.gather(*[s.on_event(event) for s in self._subscribers],
                             return_exceptions=True)  # Never block the producer
```

**Hook bridge:** The `.claude/hooks/post-tool-use.sh` script fires an HTTP `POST` to `http://oak-api:8000/internal/events` on every tool completion. The API endpoint deserialises and publishes to the `EventBus`. This keeps the bash hooks thin (one `curl` call) and all subscriber logic in testable Python.

---

### 2.4 Chain of Responsibility — Tool Validation

**Where used:** `docker/claude-harness/scripts/tool-proxy.sh`, `.claude/hooks/pre-tool-use.sh`.

**What it solves:** Tool validation has two independent layers (harness proxy and Claude Code hook) that must remain independently updateable without cross-knowledge. The Chain of Responsibility pattern makes each layer explicitly responsible for its own threat class and able to halt the chain or pass through to the next handler.

**Implementation contract (Python reference model for the bash chain):**

```python
# memory/validation_chain.py
__pattern__ = "ChainOfResponsibility"

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ToolCall:
    command: str
    agent_id: str
    problem_uuid: str

@dataclass
class ValidationResult:
    allowed: bool
    reason: str

class ToolValidator(ABC):
    _next: "ToolValidator | None" = None

    def set_next(self, handler: "ToolValidator") -> "ToolValidator":
        self._next = handler
        return handler

    async def validate(self, call: ToolCall) -> ValidationResult:
        result = await self._check(call)
        if not result.allowed:
            return result
        if self._next:
            return await self._next.validate(call)
        return ValidationResult(allowed=True, reason="all checks passed")

    @abstractmethod
    async def _check(self, call: ToolCall) -> ValidationResult: ...

class HardDenyListValidator(ToolValidator):
    """Layer 1 (tool-proxy.sh equivalent): system-destruction patterns."""
    ...

class OAKDenyListValidator(ToolValidator):
    """Layer 2 (pre-tool-use.sh equivalent): OAK business-logic patterns
    (no direct commits to main, no DROP TABLE without approval)."""
    ...

class ResourceCapValidator(ToolValidator):
    """Layer 3: reject tool calls that would exceed resource caps."""
    ...
```

**Shared pattern source:** Both bash scripts and the Python reference model read deny patterns from `scripts/deny-patterns.txt` (one pattern per line). The bash scripts use `grep -qi`; the Python model uses `re.search`. The text file is the single source of truth, as required by spec §4.6.

---

### 2.5 Repository — Memory and Skill Access

**Where used:** `memory/episodic.py`, `memory/skills.py`, `memory/redis_client.py`, `oak_mcp/`.

**What it solves:** Agent code should never contain raw SQL or Redis commands. The Repository pattern provides a typed interface for all persistence operations, making storage backends replaceable independently of the agents that use them.

**Implementation contract:**

```python
# memory/interfaces.py
__pattern__ = "Repository"

from abc import ABC, abstractmethod
from uuid import UUID

class EpisodicMemoryRepository(ABC):
    @abstractmethod
    async def store(self, episode: Episode) -> UUID: ...

    @abstractmethod
    async def retrieve_similar(self, query_embedding: list[float],
                               top_k: int = 5) -> list[Episode]: ...

    @abstractmethod
    async def mark_retrieved(self, episode_id: UUID) -> None: ...

class SkillRepository(ABC):
    @abstractmethod
    async def find_by_keywords(self, query: str, category: str | None = None,
                               top_k: int = 5) -> list[Skill]: ...

    @abstractmethod
    async def promote(self, skill_id: UUID) -> None: ...

    @abstractmethod
    async def deprecate(self, skill_id: UUID, reason: str) -> None: ...

class WorkingMemoryRepository(ABC):
    """Redis-backed; all keys are TTL-scoped to OAK_SESSION_TTL_HOURS."""
    @abstractmethod
    async def set(self, agent_id: str, key: str, value: str) -> None: ...

    @abstractmethod
    async def get(self, agent_id: str, key: str) -> str | None: ...

    @abstractmethod
    async def restore_session(self, agent_id: str) -> SessionState: ...
```

**Concrete implementations** (`PostgresEpisodicMemoryRepository`, `FilesystemSkillRepository`, `RedisWorkingMemoryRepository`) are injected at startup via the configuration-driven DI container (see §4). Tests always inject `InMemoryEpisodicMemoryRepository`, `InMemorySkillRepository`, and `InMemoryWorkingMemoryRepository` — implementations that store data in plain Python dicts, with no database dependency.

---

### 2.6 State Machine — Task Lifecycle

**Where used:** `api/routers/tasks.py`, `api/db/schema.sql`, `.claude/hooks/task-completed.sh`.

**What it solves:** The `tasks` table has a constrained set of valid status transitions (`pending → claimed → complete | failed`). Illegal transitions (e.g., `pending → complete` without passing through `claimed`) must be rejected at the application layer, not just the database CHECK constraint.

**Implementation contract:**

```python
# api/state_machines/task.py
__pattern__ = "StateMachine"

from enum import Enum
from typing import Callable

class TaskStatus(str, Enum):
    PENDING  = "pending"
    CLAIMED  = "claimed"
    COMPLETE = "complete"
    FAILED   = "failed"

# Adjacency map: key is current state; value is set of legal next states.
TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING:  {TaskStatus.CLAIMED, TaskStatus.FAILED},
    TaskStatus.CLAIMED:  {TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.PENDING},
    TaskStatus.COMPLETE: set(),   # Terminal
    TaskStatus.FAILED:   {TaskStatus.PENDING},  # Retry
}

class TaskStateMachine:
    def __init__(self, initial: TaskStatus,
                 on_transition: Callable[[TaskStatus, TaskStatus], None] | None = None):
        self._state = initial
        self._on_transition = on_transition

    @property
    def state(self) -> TaskStatus:
        return self._state

    def transition(self, to: TaskStatus) -> None:
        if to not in TASK_TRANSITIONS[self._state]:
            raise IllegalTransitionError(
                f"Cannot move task from {self._state} to {to}")
        prev = self._state
        self._state = to
        if self._on_transition:
            self._on_transition(prev, to)
```

**Judge guard integration:** The `complete` transition is only available after `task-completed.sh` verifies a PASS verdict in `judge_verdicts`. The state machine is the enforcement point; the hook is the trigger. Neither alone is sufficient.

---

### 2.7 Template Method — Agent Task Execution

**Where used:** `.claude/agents/` (each subagent definition), `api/routers/agents.py`.

**What it solves:** Every agent session follows the same lifecycle skeleton — restore session, read problem context, execute role-specific work, update state, report — but the role-specific middle step varies wildly between a Data Engineer and a Software Architect. The Template Method pattern defines the skeleton once and delegates the variable step to the concrete subclass (i.e., each agent's CLAUDE.md system prompt).

**Lifecycle skeleton (enforced via CLAUDE.md structure):**

```
1. RESTORE        → oak-session restore (identical for all agents)
2. ORIENT         → read PROBLEM.md + claim task from tasks table
3. SKILL_QUERY    → oak-skills MCP: find matching permanent skills
4. EXECUTE        → role-specific work (ingest | analyse | model | synthesise | judge)
5. VALIDATE       → run applicable checks (ruff/mypy for code agents; schema for DE)
6. REPORT         → write outputs to problem worktree + update mailbox
7. CLOSE          → attempt TaskCompleted → blocked by task-completed.sh if no PASS
8. SAVE           → oak-session save (identical for all agents)
```

Steps 1, 2, 3, 7, and 8 are identical across all agents and are defined once in the root `CLAUDE.md`. Step 4 is the only variable step; it is entirely defined by each agent's `.claude/agents/{role}.md`.

---

### 2.8 Decorator — Harness Wrapping

**Where used:** `docker/claude-harness/Dockerfile`, `docker/claude-harness/scripts/`.

**What it solves:** The OAK Harness adds behaviour (session state restore, tool call interception, API routing) to the base Claude Code binary without modifying it. This is precisely the Decorator pattern: a base object (Claude Code) wrapped by successive layers each adding a concern.

**Layer stack (innermost to outermost):**

```
Claude Code binary
    └─ decorated by: tool-proxy.sh       (deny-list filtering, command logging)
        └─ decorated by: oak-session     (session restore at start, save at end)
            └─ decorated by: oak-api-proxy  (API routing, escalation, telemetry)
```

Each layer knows only about the layer below it. The tool-proxy does not know about session state. The API proxy does not know about the deny-list. Behaviour is composed, not entangled.

---

### 2.9 Event-Driven Architecture — Pub/Sub Backbone

**Where used:** `api/ws/stream.py`, Redis pub/sub channels, `.claude/hooks/`, `memory/redis_client.py`.

**What it solves:** Agent sessions run in separate containers with no shared memory. Communication between agents (via mailbox) and between agents and the Hub (via WebSocket stream) must be asynchronous, durable within TTL, and non-blocking. Redis pub/sub provides the transport; OAK defines the channel naming convention and event schema.

**Channel naming convention:**

| Channel | Purpose | Publisher | Subscribers |
|---|---|---|---|
| `oak:stream:{problem_uuid}` | Live agent events → Hub WebSocket | All agents via API | WebSocket handler, telemetry |
| `oak:mailbox:{agent_id}` | Peer-to-peer agent messages | Any agent | Named recipient agent |
| `oak:broadcast:{problem_uuid}` | Task availability announcements | Orchestrator | All agents for the problem |
| `oak:blocked:{agent_id}` | Denied tool call log | tool-proxy.sh | Security telemetry |

**Event envelope schema (all channels):**

```json
{
  "event_type": "string",
  "agent_id": "string",
  "problem_uuid": "string",
  "timestamp_utc": 1234567890.123,
  "schema_version": "1.0",
  "payload": {}
}
```

The `schema_version` field enables rolling upgrades: new event types can be added without breaking existing subscribers that don't know about them.

---

### 2.10 Anti-Pattern Registry

The following patterns are explicitly forbidden in OAK. Every PR review must check for these. The list is additive — new anti-patterns discovered in review are added here, not silently absorbed into the codebase.

#### AP-1: God Orchestrator

**What it looks like:** The `Orchestrator` class or agent definition accumulates coordination logic that belongs elsewhere: task state transitions inside the orchestrator's system prompt, routing decisions, skill promotion triggers, WebSocket publishing. The orchestrator grows to be the only place that "understands" the system.

**Why it is fatal:** It cannot be tested in isolation, cannot be replicated across problems without carrying the entire stateful world with it, and breaks the Observer and State Machine patterns that keep coordination logic in defined components.

**Correct structure:** The Orchestrator's only job is to decompose problems into tasks and spawn agents. State transitions belong in `TaskStateMachine`. Events belong in `EventBus`. Skill promotion belongs in `SkillRepository`. If the orchestrator's CLAUDE.md system prompt exceeds 800 words, treat that as a smell that logic is being absorbed that belongs elsewhere.

#### AP-2: Inline Routing Conditionals

**What it looks like:**
```python
# In oak-api-proxy/main.py — FORBIDDEN
if response_text.startswith("I cannot") or len(response_text.split()) < 20:
    route_to_claude_api()
elif model == "qwen3-coder" and task_type == "etl":
    keep_local()
```

**Why it is fatal:** Every new routing case requires modifying the proxy's core logic, making the proxy untestable except through end-to-end runs. The `should_escalate` logic fragment is invisible to the test suite unless it is a named `RoutingStrategy` class under `strategies.py`.

**Correct structure:** All routing decisions live in a `RoutingStrategy` subclass. The proxy calls `routing_strategy.should_escalate(request, response)` — a single delegated call. New routing behaviour = new `RoutingStrategy` class + new `ROUTING_STRATEGY` enum value + new unit tests. The proxy's `proxy()` function never changes.

#### AP-3: Direct `os.environ` Access

**What it looks like:**
```python
# In any file other than api/config.py — FORBIDDEN
import os
max_agents = int(os.environ.get("MAX_AGENTS_PER_PROBLEM", 10))
api_key = os.environ["ANTHROPIC_API_KEY_REAL"]
```

**Why it is fatal:** Configuration bypasses `OAKSettings` validation. A misconfigured key is discovered at the call site during a live problem run rather than at startup. Tests cannot override configuration cleanly without `monkeypatch` or environment manipulation, breaking the DI contract.

**Correct structure:** `from api.config import settings`. Nothing else. `api/config.py` is the only file permitted to read `os.environ`. Enforced statically by a `ruff` custom rule flagging `os.environ` imports outside `api/config.py`.

#### AP-4: Fat Hooks

**What it looks like:** `.claude/hooks/post-tool-use.sh` contains 100+ lines of bash that parses tool output, makes routing decisions, writes directly to PostgreSQL, and publishes events — all inline.

**Why it is fatal:** Bash hooks cannot be unit tested reliably, their logic is invisible to the EventBus subscriber registry, and any bug in the hook silently drops telemetry without alerting the agent. Hook complexity compounds rapidly as new event types are added.

**Correct structure:** Every hook is a thin relay. The hook's only permitted operations are: (1) collect the tool context from environment variables, (2) POST to `http://oak-api:8000/internal/events` with the serialised `AgentEvent`, (3) exit 0. All business logic lives in typed Python `EventSubscriber` classes that can be unit tested with no bash involvement. A hook that does more than call the API endpoint is a violation.

#### AP-5: Probationary Skill Bypass

**What it looks like:** An agent or the Skill Extractor writes directly to `skills/permanent/` without going through the probationary queue, or marks a skill as permanent after a single use because the problem seemed "high confidence".

**Why it is fatal:** It breaks the `OAK_SKILL_PROMO_THRESHOLD` invariant and allows one-off solutions to pollute the permanent library. Future agents will retrieve and apply a skill that was never verified on a second independent problem, potentially compounding a bad solution pattern.

**Correct structure:** The `SkillRepository.promote()` method is the only promotion path. It checks `use_count >= settings.oak_skill_promo_threshold` and raises `PromotionThresholdNotMet` if the invariant is violated. Agents and the Skill Extractor call only `SkillRepository.add_use()` and `SkillRepository.request_promotion()` — the repository enforces the gate, not the caller.

---

## 3. Test-Driven Development Workflow

### 3.1 The Discipline

Every functional requirement in this PRD and in spec §14 has a corresponding test that must be written *before* the implementation. The sequence is:

1. **Red** — write a test that describes the required behaviour; confirm it fails for the right reason (not import error, not syntax error — the actual assertion fails because the feature is absent).
2. **Green** — write the minimum code to make the test pass. No gold-plating.
3. **Refactor** — improve structure, extract abstractions, apply patterns. Tests must still be green afterwards.

This is not negotiable. PRs that introduce production code without a corresponding test are rejected at CI.

### 3.2 Test Categories and Scope

```
tests/
├── unit/                   # No I/O. Everything external is mocked or in-memory.
│   ├── test_agent_factory.py
│   ├── test_routing_strategies.py
│   ├── test_task_state_machine.py
│   ├── test_tool_validation_chain.py
│   ├── test_skill_repository.py
│   └── test_event_bus.py
├── integration/            # Real database (test container), real Redis, no Docker.
│   ├── test_api_problems.py
│   ├── test_api_tasks.py
│   ├── test_api_skills.py
│   ├── test_episodic_memory.py
│   ├── test_skill_promotion.py
│   └── test_websocket_stream.py
├── contract/               # Verifies Harness and proxy honour their published contracts.
│   ├── test_tool_proxy_deny_list.py   # Runs tool-proxy.sh as subprocess
│   ├── test_session_state.py          # Round-trip state via real Redis container
│   └── test_api_proxy_routing.py     # Mocked Ollama + mocked Claude API
├── smoke/                  # Per-environment happy paths; run post-deploy.
│   ├── test_bootstrap_sequence.py     # Verifies all services come up healthy
│   ├── test_csv_to_app_pipeline.py    # Phase 0: non-agent end-to-end
│   └── test_agent_team_etl.py         # Phase 2+: Orchestrator + DE + Judge
└── system/                 # Full end-to-end on a real problem; Phase 3+ only.
    ├── test_skill_compounding.py      # 3× same problem type; verify reuse + time drop
    └── test_concurrent_problems.py   # 3 concurrent; verify isolation + no leakage
```

### 3.3 Mock Hierarchy

External dependencies are mocked in layers. Each test category uses a specific layer; mixing layers is forbidden.

| Layer | Used in | Provides |
|---|---|---|
| In-memory stubs | `unit/` | `InMemorySkillRepository`, `InMemoryEpisodicMemoryRepository`, `InMemoryWorkingMemory`, `FakeEventBus` |
| Test containers | `integration/` | Real PostgreSQL + pgvector (via `testcontainers-python`), real Redis. No Docker-in-Docker. |
| HTTP mocks | `contract/` | `respx` for mocking Ollama and Claude API HTTP endpoints; real Redis container for session tests |
| Real stack (subset) | `smoke/` | `docker compose --profile test up` — all services except `oak-harness` (replaced by test harness) |
| Full stack | `system/` | All services running; real Claude Code agent sessions against Ollama |

### 3.4 Fixtures and Factories

All test setup is performed via pytest fixtures and test factories. No test-specific data is hardcoded.

```python
# tests/conftest.py

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# ── Module-level pattern enforcement ──────────────────────────────────────────
def pytest_collect_file(parent, file_path):
    """Fail collection if a production module lacks __pattern__ attribute."""
    ...

# ── Database fixtures ──────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg

@pytest.fixture
def db_session(pg_container):
    """Fresh transaction per test; rolled back after each test. No teardown SQL."""
    ...

# ── Redis fixture ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as r:
        yield r

@pytest.fixture
def redis_client(redis_container):
    """Flushed before each test to guarantee isolation."""
    ...

# ── Test data factories ────────────────────────────────────────────────────────
@pytest.fixture
def make_problem(db_session):
    """Returns a callable that creates a problem row with sensible defaults."""
    def _make(**kwargs) -> Problem:
        defaults = {"title": "Test Problem", "status": "pending",
                    "description": "Auto-generated test problem"}
        return Problem(**{**defaults, **kwargs})
    return _make

@pytest.fixture
def make_task(db_session, make_problem):
    ...

@pytest.fixture
def make_skill():
    ...

@pytest.fixture
def mock_agent_factory():
    """Returns a DeterministicAgentFactory that never touches Docker."""
    ...
```

### 3.5 Coverage Requirements

Coverage is tracked per test category. The CI gate blocks merge if any category is below its threshold.

| Test category | Coverage target | Measured over |
|---|---|---|
| Unit | 90% line coverage | `api/`, `memory/`, `oak_mcp/oak-api-proxy/` |
| Integration | 80% line coverage | All `api/routers/` endpoints |
| Contract | 100% of documented contracts | tool-proxy deny list, session round-trip, proxy routing decisions |
| Smoke | N/A (binary pass/fail) | Happy path per Phase |
| System | N/A (binary pass/fail) | Defined exit criteria from spec §14 |

Mutation testing (`mutmut`) is run on the `unit/` suite at Phase 1 and above. A mutation score below 70% triggers a mandatory refactor of the relevant module before it proceeds to integration.

### 3.6 Phase-Gated Test Progression

The test suite grows with the Phase roadmap. Each phase introduces new test files and must meet a concrete minimum count; **existing tests must not break**. "Minimum assertions" counts mean distinct `assert` statements across the phase's new test files, not trivially trivial ones (`assert True` does not count).

| Phase | New test files | Minimum tests introduced | Minimum assertions | Gate check |
|---|---|---|---|---|
| 0 | `unit/test_api_problems.py`, `unit/test_task_state_machine.py` (transitions only), `smoke/test_bootstrap_sequence.py`, `smoke/test_csv_to_app_pipeline.py` | ≥ 8 unit tests, ≥ 1 smoke test | ≥ 20 | All unit and smoke pass; CSV → table + `app.py` pipeline verified with no agent involvement; all 4 illegal task transitions verified to raise |
| 1 | `contract/test_tool_proxy_deny_list.py`, `contract/test_session_state.py`, `contract/test_api_proxy_routing.py`, `unit/test_routing_strategies.py` | ≥ 12 contract tests (≥ 6 deny-list patterns tested both directions), ≥ 4 strategy unit tests | ≥ 30 | All contract tests pass; mutation score ≥ 70% on harness + proxy modules; `PassthroughStrategy.should_escalate()` returns `False` on every input in a parameterised test of ≥ 10 varied responses |
| 2 | `integration/test_api_tasks.py`, `unit/test_event_bus.py`, `integration/test_api_problems.py` (cap enforcement), `smoke/test_agent_team_etl.py` | ≥ 10 integration tests, ≥ 5 event bus unit tests, ≥ 1 smoke test | ≥ 35 | All integration tests pass; task state machine has 100% transition coverage (all 4 states × all valid and invalid edges tested); `MAX_CONCURRENT_PROBLEMS` cap returns 429 on N+1 POST |
| 3 | `integration/test_skill_promotion.py`, `integration/test_episodic_memory.py`, `integration/test_websocket_stream.py`, `system/test_skill_compounding.py` | ≥ 8 integration tests, ≥ 1 system test | ≥ 25 | Skill promotion round-trip passes; compounding wall-clock metric captured in system test output; pgvector similarity query returns correct skill as top-1 result on 5 known queries |
| 4 | Extend smoke/system tests for `OAK_MODE=mini`; `unit/test_stall_detection_strategy.py` with golden response set | ≥ 6 stall detection unit tests against a ≥ 20-item golden set | ≥ 20 | Stall detection false positive rate < 5% on golden set; false negative rate < 20% (i.e., known-bad responses are caught); Mac Mini smoke suite passes with no code changes |
| 5 | `system/test_concurrent_problems.py` | ≥ 1 system test covering 3 concurrent problems | ≥ 5 | 3 concurrent problems complete; zero cross-problem data leakage (verified by attempting cross-UUID query); all resource cap counters visible in `GET /api/telemetry` |

### 3.7 Test Naming Convention

All test function names follow the pattern: `test_{unit_under_test}__{condition}__{expected_outcome}`.

Examples:
- `test_task_state_machine__pending_to_complete_direct__raises_illegal_transition`
- `test_stall_detection_strategy__empty_response__returns_true`
- `test_skill_repository__find_by_keywords__returns_top_k_ordered_by_similarity`
- `test_tool_proxy__rm_rf_root__exits_with_code_2`

This convention makes test intent readable without opening the test body, and it makes failures immediately interpretable in CI output.

---

## 4. Configuration-Driven Architecture

### 4.1 Philosophy

OAK has exactly **one place to change any configurable behaviour**: the `.env` file (or environment variables set by Docker Compose). No threshold, timeout, model name, feature flag, or platform difference is hardcoded anywhere in the application code. Every value has a typed default validated at startup; misconfiguration is a runtime error before any work begins, not a silent bug discovered during a problem run.

### 4.2 Pydantic Settings Model

All configuration is represented as a single `OAKSettings` Pydantic model. This model is instantiated once at application startup and injected via FastAPI's dependency system. No module reads `os.environ` directly.

```python
# api/config.py
__pattern__ = "Configuration"

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from enum import Enum

class OAKMode(str, Enum):
    DGX   = "dgx"
    MINI  = "mini"
    CLOUD = "cloud"

class RoutingStrategy(str, Enum):
    PASSTHROUGH  = "passthrough"
    STALL        = "stall"
    CONFIDENCE   = "confidence"

class OAKSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore", case_sensitive=False)

    # ── Platform ────────────────────────────────────────────────────────────
    oak_mode: OAKMode = OAKMode.DGX

    # ── Inference ────────────────────────────────────────────────────────────
    anthropic_base_url: str     = "http://oak-api-proxy:9000"
    anthropic_auth_token: str   = "ollama"
    anthropic_api_key: str      = ""          # Empty = local-only
    anthropic_api_key_real: str = ""          # Used by proxy for escalation
    default_model: str          = "llama3.3:70b"
    coder_model: str            = "qwen3-coder"
    analysis_model: str         = "glm-4.7"

    # ── Routing strategy ─────────────────────────────────────────────────────
    routing_strategy: RoutingStrategy = RoutingStrategy.PASSTHROUGH
    stall_detection_enabled: bool     = False
    stall_min_tokens: int             = 20
    stall_phrases: list[str]          = Field(
        default=["i cannot", "i don't know how", "i'm unable", "as an ai"])
    local_confidence_threshold: float = 0.8

    # ── Resource caps ────────────────────────────────────────────────────────
    max_agents_per_problem: int   = 10
    max_concurrent_problems: int  = 3
    max_harness_containers: int   = 20

    # ── Memory ───────────────────────────────────────────────────────────────
    database_url: str                 = "postgresql://oak:oak@oak-postgres:5432/oak"
    redis_url: str                    = "redis://oak-redis:6379"
    oak_session_ttl_hours: int        = 24
    oak_memory_ttl_days: int          = 90

    # ── Skill library ─────────────────────────────────────────────────────────
    oak_skill_promo_threshold: int    = 2
    skill_probationary_path: str      = "/workspace/skills/probationary"
    skill_permanent_path: str         = "/workspace/skills/permanent"

    # ── Agent behaviour ──────────────────────────────────────────────────────
    oak_idle_timeout_seconds: int     = 120
    claude_code_experimental_agent_teams: str = "1"

    # ── Observability ────────────────────────────────────────────────────────
    telemetry_enabled: bool           = True
    stall_escalation_alert_threshold: float = 0.3   # Alert if > 30% of calls escalate

    @model_validator(mode="after")
    def validate_escalation_config(self) -> "OAKSettings":
        if self.stall_detection_enabled and not self.anthropic_api_key_real:
            # Not a hard error — proxy will log and fall back to local
            import warnings
            warnings.warn(
                "STALL_DETECTION_ENABLED=true but ANTHROPIC_API_KEY_REAL is empty. "
                "Escalation will be attempted and silently fall back to Ollama response.",
                stacklevel=2)
        return self

    @model_validator(mode="after")
    def validate_resource_caps(self) -> "OAKSettings":
        if self.oak_mode == OAKMode.MINI and self.max_agents_per_problem > 4:
            import warnings
            warnings.warn(
                f"OAK_MODE=mini but MAX_AGENTS_PER_PROBLEM={self.max_agents_per_problem}. "
                "Mini profile recommends ≤ 4 agents per problem due to memory constraints.",
                stacklevel=2)
        return self

# Singleton — imported by all modules
settings = OAKSettings()
```

### 4.3 Platform Profile Defaults

Rather than `if oak_mode == DGX: ...` conditionals in application code, each platform profile defines its own `.env.{profile}` that overrides defaults. The Docker Compose platform files set `env_file` to the appropriate profile file.

```bash
# .env.dgx
OAK_MODE=dgx
DEFAULT_MODEL=llama3.3:70b
CODER_MODEL=qwen2.5-coder:32b
ANALYSIS_MODEL=llama3.3:70b
MAX_AGENTS_PER_PROBLEM=10
MAX_CONCURRENT_PROBLEMS=3
MAX_HARNESS_CONTAINERS=20
ROUTING_STRATEGY=passthrough

# .env.mini
OAK_MODE=mini
DEFAULT_MODEL=llama3.2:8b
CODER_MODEL=qwen2.5-coder:7b
ANALYSIS_MODEL=llama3.2:3b
MAX_AGENTS_PER_PROBLEM=4
MAX_CONCURRENT_PROBLEMS=1
MAX_HARNESS_CONTAINERS=5
ROUTING_STRATEGY=confidence
LOCAL_CONFIDENCE_THRESHOLD=0.7
STALL_DETECTION_ENABLED=true

# .env.cloud
OAK_MODE=cloud
DEFAULT_MODEL=llama3.3:70b
CODER_MODEL=qwen2.5-coder:32b
ANALYSIS_MODEL=llama3.3:70b
MAX_AGENTS_PER_PROBLEM=15
MAX_CONCURRENT_PROBLEMS=10
MAX_HARNESS_CONTAINERS=60
ROUTING_STRATEGY=stall
STALL_DETECTION_ENABLED=true
```

**Adding a new platform** requires only a new `.env.{profile}` file and a `docker-compose.{profile}.yml` file. Zero application code changes.

### 4.4 Feature Flags

Feature flags are a subset of `OAKSettings`. Every optional capability from spec §1.4 is a flag.

| Flag | Type | Default | Controls |
|---|---|---|---|
| `stall_detection_enabled` | bool | `false` | Whether `oak-api-proxy` escalates on stall detection |
| `telemetry_enabled` | bool | `true` | Whether `post-tool-use.sh` writes to `agent_telemetry` |
| `skill_extraction_enabled` | bool | `true` | Whether `task-completed.sh` triggers the Skill Extractor |
| `meta_agent_enabled` | bool | `false` | Whether the Meta Agent schedule is active (v1.1+) |
| `ui_evolution_enabled` | bool | `false` | Whether Software Architect opens UI PRs (v1.1+) |
| `concurrent_problems_enabled` | bool | `false` | Whether TRUNK accepts >1 active problem simultaneously |
| `judge_required` | bool | `true` | Whether Judge PASS is required before task closure |

Disabling `judge_required` is permitted for development/debugging only. It must not be disabled in any environment where problem outputs could be acted upon.

### 4.5 Dependency Injection

All dependencies on `OAKSettings`, repositories, and the `EventBus` are injected via FastAPI's `Depends` system. No module instantiates its own dependencies. This makes every API endpoint trivially testable: tests inject a `TestSettings` object and in-memory repositories without any patching.

```python
# api/dependencies.py

from functools import lru_cache
from api.config import OAKSettings
from memory.interfaces import SkillRepository, EpisodicMemoryRepository, WorkingMemoryRepository
from memory.postgres_episodic import PostgresEpisodicMemoryRepository   # production
from memory.filesystem_skills import FilesystemSkillRepository           # production
from memory.redis_working import RedisWorkingMemoryRepository            # production
from api.events.bus import EventBus

@lru_cache
def get_settings() -> OAKSettings:
    return OAKSettings()

def get_skill_repository(settings: OAKSettings = Depends(get_settings)) -> SkillRepository:
    return FilesystemSkillRepository(
        permanent_path=settings.skill_permanent_path,
        probationary_path=settings.skill_probationary_path,
        db_url=settings.database_url)

def get_episodic_memory(settings: OAKSettings = Depends(get_settings)) -> EpisodicMemoryRepository:
    return PostgresEpisodicMemoryRepository(db_url=settings.database_url)

def get_event_bus() -> EventBus:
    return EventBus()  # Configured at application startup with registered subscribers
```

**Test override pattern:**

```python
# tests/integration/test_api_problems.py
from api.dependencies import get_settings, get_skill_repository
from tests.fakes import InMemorySkillRepository, TestSettings

app.dependency_overrides[get_settings]          = lambda: TestSettings()
app.dependency_overrides[get_skill_repository]  = lambda: InMemorySkillRepository()
```

No monkeypatching, no `unittest.mock.patch`. Overrides are explicit and scoped to the test module.

### 4.6 Configuration Validation at Startup

`OAKSettings` validation runs at import time. If any required value is missing or invalid, the application refuses to start with a clear error message identifying the offending field. There is no "warn and continue" for required values.

A startup health check endpoint (`GET /health`) reports the current effective configuration (with sensitive fields redacted) so operators can confirm what the running system actually sees:

```json
{
  "status": "healthy",
  "oak_mode": "dgx",
  "routing_strategy": "passthrough",
  "stall_detection_enabled": false,
  "max_agents_per_problem": 10,
  "max_concurrent_problems": 3,
  "api_key_present": false,
  "models": {
    "default": "llama3.3:70b",
    "coder": "qwen2.5-coder:32b",
    "analysis": "llama3.3:70b"
  },
  "feature_flags": {
    "telemetry_enabled": true,
    "skill_extraction_enabled": true,
    "meta_agent_enabled": false,
    "ui_evolution_enabled": false
  }
}
```

### 4.7 Configuration Schema Reference

Every configurable value in OAK is listed here. This is the authoritative source: if a key exists in `.env` but not in this table, it is not a supported configuration key and will be ignored (or cause an `extra="ignore"` silent skip in `OAKSettings`). **Phase introduced** is the earliest phase where the key has any functional effect.

| Key | Type | Default | Platform override | Phase introduced | Controls |
|---|---|---|---|---|---|
| `OAK_MODE` | enum | `dgx` | — | 0 | Active platform profile; selects compose file and env defaults |
| `ANTHROPIC_BASE_URL` | string | `http://oak-api-proxy:9000` | all | 0 | Where Claude Code sends API calls; always points to proxy, never directly to Ollama |
| `ANTHROPIC_AUTH_TOKEN` | string | `ollama` | all | 0 | Satisfies Ollama's auth requirement; not a real API key |
| `ANTHROPIC_API_KEY` | string | `""` | all | 0 | Intentionally empty in harness; proxy holds real key separately |
| `ANTHROPIC_API_KEY_REAL` | string | `""` | all | 4 | Real Anthropic key used by proxy on escalation; absent = fully local |
| `DEFAULT_MODEL` | string | `llama3.3:70b` | mini: `llama3.2:8b`, cloud: `llama3.3:70b` | 0 | Ollama model for reasoning/synthesis tasks |
| `CODER_MODEL` | string | `qwen3-coder` | mini: `qwen2.5-coder:7b` | 0 | Ollama model for all code generation tasks |
| `ANALYSIS_MODEL` | string | `glm-4.7` | mini: `llama3.2:3b` | 0 | Ollama model for EDA and statistical analysis |
| `ROUTING_STRATEGY` | enum | `passthrough` | mini: `confidence`, cloud: `stall` | 0 (effect) / 4 (non-passthrough) | Selects `RoutingStrategy` class in proxy; `passthrough` = no escalation |
| `STALL_DETECTION_ENABLED` | bool | `false` | mini: `true` (phase 4+) | 4 | Master toggle for heuristic escalation; `false` = `PassthroughStrategy` regardless of `ROUTING_STRATEGY` |
| `STALL_MIN_TOKENS` | int | `20` | — | 4 | Token count below which `StallDetectionStrategy` flags a response |
| `STALL_PHRASES` | list[str] | see config.py | — | 4 | Phrase prefixes triggering escalation in `StallDetectionStrategy` |
| `LOCAL_CONFIDENCE_THRESHOLD` | float | `0.8` | mini: `0.7` | 4 | Minimum confidence score for `ConfidenceThresholdStrategy` |
| `MAX_AGENTS_PER_PROBLEM` | int | `10` | mini: `4`, cloud: `15` | 2 | Hard cap enforced by `AgentFactory.launch()`; blocks spawn above limit |
| `MAX_CONCURRENT_PROBLEMS` | int | `3` | mini: `1`, cloud: `10` | 2 | Hard cap enforced by `POST /api/problems`; returns 429 when exceeded |
| `MAX_HARNESS_CONTAINERS` | int | `20` | mini: `5`, cloud: `60` | 2 | Total containers across all problems; checked in `new-problem.sh` |
| `DATABASE_URL` | string | `postgresql://oak:oak@oak-postgres:5432/oak` | all | 0 | PostgreSQL DSN; injected into all services |
| `REDIS_URL` | string | `redis://oak-redis:6379` | all | 0 | Redis DSN; used by harness, proxy, event bus, and session state |
| `OAK_SESSION_TTL_HOURS` | int | `24` | — | 1 | TTL for all Redis session keys; after expiry agent starts cold |
| `OAK_MEMORY_TTL_DAYS` | int | `90` | — | 3 | Days before episodic rows are soft-archived (not deleted) |
| `OAK_SKILL_PROMO_THRESHOLD` | int | `2` | — | 3 | Independent problem uses before probationary → permanent promotion |
| `SKILL_PROBATIONARY_PATH` | string | `/workspace/skills/probationary` | — | 3 | Filesystem path for new candidate skills |
| `SKILL_PERMANENT_PATH` | string | `/workspace/skills/permanent` | — | 3 | Filesystem path for promoted skills |
| `OAK_IDLE_TIMEOUT_SECONDS` | int | `120` | — | 2 | Seconds of no tool calls before `teammate-idle.sh` fires |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | string | `"1"` | — | 2 | Enables multi-agent teams in Claude Code; must be `"1"` |
| `TELEMETRY_ENABLED` | bool | `true` | — | 0 | Whether `post-tool-use.sh` writes to `agent_telemetry`; disable only for debugging |
| `SKILL_EXTRACTION_ENABLED` | bool | `true` | — | 3 | Whether `task-completed.sh` triggers Skill Extractor after PASS |
| `META_AGENT_ENABLED` | bool | `false` | — | v1.1+ | Whether Meta Agent schedule is active |
| `UI_EVOLUTION_ENABLED` | bool | `false` | — | v1.1+ | Whether Software Architect opens full new-page UI PRs |
| `CONCURRENT_PROBLEMS_ENABLED` | bool | `false` | cloud: `true` | 5 | Whether TRUNK accepts >1 active problem; enforces `MAX_CONCURRENT_PROBLEMS` |
| `JUDGE_REQUIRED` | bool | `true` | — | 2 | Whether Judge PASS is required before task closure; `false` is for dev only |
| `STALL_ESCALATION_ALERT_THRESHOLD` | float | `0.3` | — | 4 | Fraction of calls escalated before `/health` flags a warning |
| `UI_CHURN_RATE_LIMIT` | int | `3` | — | 3 | Problems solved before next UI PR is permitted; enforced by Software Architect hook |
| `UI_MAX_PAGES` | int | `20` | — | 3 | Maximum distinct Hub pages before Hub restructure approval required |

**Reading this table during implementation:** Before adding a new config key to `.env`, add it to this table first. The table entry is the specification; the `.env` edit and `OAKSettings` field are the implementation. PRs that add new keys to `.env` without a table update are rejected.

---

## 5. Component Design Requirements

### 5.1 TRUNK (FastAPI API Gateway)

| Requirement | Detail |
|---|---|
| Pattern | Observer (EventBus subscriber registration at startup), Repository (injected), State Machine (task transitions) |
| Error handling | All endpoints return RFC 7807 Problem Details on error; no bare 500s |
| Validation | All request bodies are Pydantic models; validation errors return 422 with field-level detail |
| Resource cap enforcement | `POST /api/problems` checks `MAX_CONCURRENT_PROBLEMS` before creating; returns 429 if exceeded |
| Idempotency | `POST /api/problems` accepts an optional `idempotency_key`; duplicate keys return the existing problem record with 200, not 422 |
| Startup | Registers all EventBus subscribers; validates `OAKSettings`; runs schema migration check |

### 5.2 GROVE (Agent Engine)

| Requirement | Detail |
|---|---|
| Pattern | Factory (agent creation), Template Method (lifecycle), Chain of Responsibility (validation) |
| Agent spawn | Orchestrator calls `POST /api/agents/spawn` with `{role, problem_uuid}`; TRUNK calls `AgentFactory.launch()`; container name must match `oak-agent-{problem_uuid}-{role}` |
| Resource cap | Factory checks `MAX_AGENTS_PER_PROBLEM` before launching; raises `ResourceCapExceeded` if exceeded |
| Idle detection | `teammate-idle.sh` fires at `OAK_IDLE_TIMEOUT_SECONDS`; injects structured prompt; logs to telemetry |
| Termination | Containers exit on task completion; orphan detection runs every 5 minutes via `scripts/cleanup-orphans.sh` |

### 5.3 OAK Harness

| Requirement | Detail |
|---|---|
| Pattern | Decorator (wrapping Claude Code), Chain of Responsibility (validation layers) |
| Deny patterns | Read from `scripts/deny-patterns.txt` at runtime; changes take effect without image rebuild |
| Session state | All five state categories (open files, cmd history, cwd, git state, env vars) must round-trip through container restart |
| Proxy contract | `ANTHROPIC_BASE_URL` always points to `oak-api-proxy`; never directly to Ollama or Anthropic |
| No host filesystem | `/workspace` is the only permitted write target; mount is read-only outside `/workspace` and `/mnt/oak-data` |

### 5.4 Memory System

| Requirement | Detail |
|---|---|
| Pattern | Repository (all three layers), Observer (episodic writes triggered by EventBus events) |
| pgvector | Embeddings are 1536-dimensional (OpenAI-compatible); generated by a local embedding model or Ollama `nomic-embed-text` |
| TTL enforcement | Redis keys expire at `OAK_SESSION_TTL_HOURS`; episodic rows are soft-deleted after `OAK_MEMORY_TTL_DAYS` (not hard deleted — archived with `archived_at` timestamp) |
| Skill promotion | Promotion to `permanent` requires exactly `OAK_SKILL_PROMO_THRESHOLD` independent problem uses (not re-uses within the same problem) |
| Concurrency | Skill promotion uses PostgreSQL advisory locks to prevent double-promotion under concurrent problem loads |

### 5.5 UI Canopy (Streamlit Hub)

| Requirement | Detail |
|---|---|
| No data storage | The Hub holds no problem data locally; all state comes from TRUNK API calls |
| WebSocket reconnect | WebSocket client in `pages/02_problem_status.py` must exponential-backoff reconnect on drop (max 5 attempts, then show "connection lost" banner) |
| Sensitive data | Problem data is never displayed raw in the Hub; only titles, statuses, and aggregated metrics are shown |
| UI PR quality gate | Software Architect PRs against `oak/ui` must pass `ruff`, `mypy`, and a Streamlit smoke test (import + `st.empty()` render) in CI before merge is permitted |
| New page constraint (v1) | Software Architect is permitted to add analytics tabs to existing pages only; full new page generation is a v1.1 capability (controlled by `ui_evolution_enabled` flag) |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Target | Measured by |
|---|---|---|
| API P95 response time | < 200ms for all non-streaming endpoints | `agent_telemetry` + API access log |
| WebSocket event latency | < 500ms from agent event to Hub display | End-to-end timing in system tests |
| pgvector skill query | < 200ms for top-5 retrieval at library size ≤ 1000 skills | Integration test timing assertion |
| Session restore time | < 2s from container start to first tool call available | Smoke test timing |
| Proxy overhead | < 50ms added latency vs direct Ollama call | Contract test timing comparison |

### 6.2 Reliability

| Metric | Target |
|---|---|
| Problem success rate | ≥ 80% of problems reach `complete` status on first attempt (Phase 2+) |
| Harness restart recovery | Agent sessions recoverable from Redis state after container restart with no re-ingestion required |
| Data isolation | Zero cross-problem data leakage verified by system test (random cross-problem query returns empty result) |
| Skill promotion correctness | Zero false promotions (skills promoted with fewer than `OAK_SKILL_PROMO_THRESHOLD` uses); verified by integration test |

### 6.3 Maintainability

| Requirement | Implementation |
|---|---|
| Pattern declaration | Every production module must declare `__pattern__`; enforced at test collection time |
| Cyclomatic complexity | No function exceeds complexity 10 (`ruff` rule `C901`); CI blocks merge if violated |
| Type coverage | `mypy --strict` passes on all `api/` and `memory/` modules (Phase 1+) |
| Docstring coverage | All public classes and functions have docstrings; enforced by `pydocstyle` |
| Dead code | `vulture` runs weekly; any dead code > 10 lines triggers a cleanup issue |

### 6.4 Security

| Requirement | Implementation |
|---|---|
| No external network from harness | Docker network `oak-net` is bridge-isolated; harness containers have no internet access |
| Deny-list immutability | `scripts/deny-patterns.txt` is mounted read-only into harness containers; agents cannot modify it |
| Secret handling | `ANTHROPIC_API_KEY_REAL` is never logged, never returned by `/health`, and never written to `agent_telemetry` |
| PostgreSQL access | Agents access PostgreSQL only through MCP server (`oak-memory-mcp`, `oak-skills-mcp`); direct `psql` access from agent containers is blocked at the Docker network layer |
| Worktree isolation | `git worktree add` for each problem creates an isolated branch; `git push --force` to `main` is blocked by a pre-receive hook on the remote |

---

## 7. Acceptance Criteria Matrix

Each row maps a spec objective (spec §1.1) to its acceptance test and the phase it must pass by.

| Objective | Acceptance test | Phase gate |
|---|---|---|
| Autonomous problem-to-app conversion | `smoke/test_csv_to_app_pipeline.py`: 1 CSV → deployed `app.py` with no runtime errors | Phase 0 |
| Autonomous problem-to-app (agent-driven) | `smoke/test_agent_team_etl.py`: same CSV, full Orchestrator + DE + Judge flow | Phase 2 |
| Compounding skill reuse (any reduction) | `system/test_skill_compounding.py`: Problem 3 (same type as 1, 2) faster than Problem 1 | Phase 3 |
| Compounding skill reuse (50% reduction) | Same system test; median wall-clock diff ≥ 50% by Phase 5 | Phase 5 |
| Self-evolving interface | UI PR from Software Architect: passes CI, merges, Hub redeploys with new tab visible | Phase 3 (tab), Phase 4 (page) |
| Data sovereignty | No external HTTP calls from harness containers during problem run (verified by network capture in contract test) | Phase 1 |
| Platform portability | All smoke tests pass on Mac Mini with `OAK_MODE=mini` and no code changes | Phase 4 |
| Resource cap enforcement | `test_api_problems.py`: 4th `POST /api/problems` returns 429 when `MAX_CONCURRENT_PROBLEMS=3` | Phase 2 |
| Session recovery | `contract/test_session_state.py`: agent context restored after `docker stop` + `docker start` | Phase 1 |
| Skill promotion correctness | `integration/test_skill_promotion.py`: skill with 1 use stays `probationary`; skill with 2+ uses promotes | Phase 3 |

---

## 8. Development Conventions

### 8.1 Commit Message Format

```
type(scope): subject

body (optional)

Refs: #issue_number
```

Types: `feat`, `fix`, `test`, `refactor`, `chore`, `docs`. Scope is the layer name: `trunk`, `grove`, `harness`, `proxy`, `memory`, `canopy`, `skills`, `config`.

Examples:
- `feat(harness): add deny-patterns.txt shared source for proxy and hook`
- `test(trunk): add integration test for MAX_CONCURRENT_PROBLEMS enforcement`
- `refactor(proxy): extract StallDetectionStrategy from inline conditional`

### 8.2 Branch and PR Policy

- Feature branches always branch from `main`; never from each other.
- PRs require: all CI checks green (unit + contract + integration for the affected scope), at least one pattern declaration visible in the changed module, and a test-first evidence comment ("failing test added in commit X before implementation in commit Y").
- No direct push to `main`, `oak/agents`, `oak/skills`, or `oak/ui`.
- Agent-generated PRs (Software Architect, Meta Agent) follow the same CI gate as human PRs.

### 8.3 File Organization Rules

- One class per file for all Repository, Factory, and Strategy implementations.
- `interfaces.py` defines abstract base classes; concrete implementations are in separate files.
- Test files mirror production file structure: `memory/skills.py` → `tests/unit/test_skills.py`.
- Configuration has a single home: `api/config.py`. Any other file that needs a setting imports `from api.config import settings`.

---

*Document owner: OAK Core Team*
*Companion document: spec.md (v1.2)*
*Remote repository: https://github.com/SharathSPhD/oak.git*
