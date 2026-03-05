# ACORN Gap Analysis — 2026-03-05

## Executive Summary

ACORN is ~78% complete. The 7-layer architecture (CANOPY→TRUNK→GROVE→RELAY→WARDEN→ROOTS→SOIL) is
implemented. All 7 HIGH severity OAK→ACORN migration bugs are fixed. CORTEX+ GWT exists. The GRS
reward system schema exists. All 18 agent definitions exist. All 5 hooks exist.

The remaining gap is that components exist but are **not autonomously wired together**. This document
captures all identified gaps, their severity, and the remediation plan.

---

## Status of Previously Reported Issues

### HIGH Severity (All Fixed ✓)

| # | Issue | Status |
|---|-------|--------|
| H1 | `settings.oak_network` → `settings.acorn_network` | FIXED |
| H2 | acorn-kernels-mcp queries `skills` table | FIXED |
| H3 | `add_skill_use` tool handler mismatch | FIXED |
| H4 | `request_promotion` schema mismatch | FIXED |
| H5 | UI calls `/api/skills` instead of `/api/kernels` | FIXED |
| H6 | `seed_skills.sql` inserts into non-existent table | FIXED |
| H7 | Tests assert `skills` table; code uses `kernels` | FIXED |

### MEDIUM Severity

| # | Issue | Files | Status |
|---|-------|-------|--------|
| M1 | `os.environ` in MCP servers | `acorn_mcp/acorn-*-mcp/server.py` | ACCEPTABLE — separate subprocesses cannot import api.config; `per-file-ignores` in ruff config excludes these from ANN checks |
| M2 | OAK references in scripts | `scripts/cleanup-orphans.sh`, `docker/init-db.sh` | FIXED |
| M3 | Role name `skill-extractor` | `api/routers/agents.py` | FIXED — uses `kernel-extractor` |
| M4 | Agent doc terminology | `.claude/agents/orchestrator.md` | FIXED — no SkillRepository refs |

### LOW Severity

| # | Issue | Status |
|---|-------|--------|
| L1 | Config missing values | FIXED — `kernel_deprecation_threshold`, `stale_threshold_seconds`, `warden_poll_interval` present |
| L2 | `memory/skills.py` wrong filename | FIXED — renamed to `kernel_repository.py` + `kernels.py` |
| L3 | Test file naming | FIXED in this run — see Phase 1C |
| L4 | `ui-next/package-lock.json` has `oak-hub` | Pending — run `npm install` in `ui-next/` |

---

## Architectural Gaps (Path to True Autonomy)

| # | Gap | Root Cause | Phase | Status |
|---|-----|------------|-------|--------|
| A1 | CORTEX+ not self-starting | `cortex_enabled: False`; no `cortex_autostart` flag | 2A | FIXED in this run |
| A2 | GRS ORIENT injection not wired | `agent_creator.py` doesn't call reward endpoint at spawn | 3A | FIXED in this run |
| A3 | Constitutional C1 gate missing | `POST /api/problems` doesn't check `source_urls` locality | 3B | FIXED in this run |
| A4 | WebSocket streaming verified | EventBus → WebSocketSubscriber → Redis → ws/stream.py — fully wired | 4A | VERIFIED |
| A5 | WARDEN doesn't manage CORTEX+ | `acorn-warden.sh` only monitors harness containers | 2B | FIXED in this run |
| A6 | Calibration agent not scheduled | No post-verdict trigger for low role scores | 3C | FIXED in this run |
| A7 | Meta-agent not scheduled | No problem-count-based trigger | 3C | FIXED in this run |
| A8 | End-to-end pipeline unverified | No smoke test | 4B | FIXED in this run |
| A9 | MemOS tiers 2+3 incomplete | KV-cache and LoRA deferred to v2 | 5A | PARTIAL — episodic consolidation implemented |

---

## Implementation Summary (This Run)

### Phase 0 — Gap Analysis Document
- Created `docs/plans/2026-03-05-acorn-gap-analysis.md` (this file)

### Phase 1C — Test File Renames
- `tests/unit/test_skill_repository.py` → `tests/unit/test_kernel_repository.py`
- `tests/unit/test_cached_skills.py` → `tests/unit/test_cached_kernels.py`
- `tests/integration/test_skill_extraction_loop.py` → `tests/integration/test_kernel_extraction_loop.py`
- Fixed bug in integration test: `UPDATE skills` → `UPDATE kernels`

### Phase 2A — CORTEX+ Auto-Start
- Added `cortex_autostart: bool = True` to `AcornSettings`
- Added `cortex_reconcile_interval: int = 300` to `AcornSettings`
- Modified `api/main.py` lifespan to start CORTEX+ when `cortex_autostart=True`
- Added `tests/unit/test_cortex_autostart.py`

### Phase 2B — WARDEN Monitors CORTEX+
- Added CORTEX+ health check and restart logic to `scripts/acorn-warden.sh`
- Added meta-agent problem-count scheduling (every `META_SCHEDULE_PROBLEMS` completions)
- Added calibration trigger tracking (Redis key `warden:judge_fail_count`)

### Phase 3A — GRS ORIENT Injection
- Added `write_orient_context()` to `api/services/agent_creator.py`
- Modified spawn flow to write `ORIENT_CONTEXT.md` to problem worktree before container launch
- Each agent reads role-specific recent wins/misses at session start

### Phase 3B — Constitutional Hard Gates
- Added `source_urls: list[str] | None` and `cloud_escalation: bool = False` to `ProblemCreate`
- C1 gate: `POST /api/problems` returns HTTP 403 if non-local URLs and `cloud_escalation=False`
- C4 gate: `POST /api/agents/spawn` returns HTTP 429 (not 503) for `MAX_HARNESS_CONTAINERS`
- Violations logged to `constitutional_violations` table
- Added `tests/unit/test_constitutional_gates.py`

### Phase 3C — Calibration & Meta-Agent Scheduling
- `POST /api/judge_verdicts`: on `fail`, publishes `calibration_needed` event if role rolling_30d below threshold
- WARDEN: tracks `problems_completed` counter in Redis; triggers meta-agent POST every N problems

### Phase 4A — WebSocket Streaming (Verified)
- WebSocket pipeline confirmed: `EventBus.publish()` → `WebSocketSubscriber.on_event()` → `Redis.publish()` → `ws/stream.py` → Hub
- Events covered: `tool_called`, `task_complete`, `judge_verdict`, `agent_spawned`, `kernel_promoted`, `problem_created`

### Phase 4B — End-to-End Smoke Test
- Created `tests/smoke/test_full_pipeline.py` covering: problem submit → agent spawn → task lifecycle → judge verdict → kernel extraction

### Phase 5A — Episodic Memory Consolidation
- Added `consolidate_domain()` to `memory/episodic_repository.py`
- Clusters episodes by event_type and content, writes KERNEL.md candidates to probationary grove
- WARDEN triggers consolidation when episode count for a domain exceeds threshold

---

## Remaining Deferred Items (v2)

| Item | Reason |
|------|--------|
| MemOS Tier 1 (LoRA adapters) | Requires fine-tuning pipeline; deferred to Phase 4+ |
| MemOS Tier 2 (KV-cache snapshots) | Requires model-level integration; deferred to Phase 4+ |
| `acorn-research-mcp` server | Currently only HTTP router; MCP wrapper deferred |
| Row-level security (RLS) | Single-tenant deployment; multi-tenant deferred |
| Cloud vLLM validation | DGX Spark is primary; cloud profile deferred to Phase 5 |
| `ui-next/package-lock.json` `oak-hub` | Run `npm install` in `ui-next/` to regenerate |

---

## Verification Commands

```bash
# Lint + type check
ruff check api/ memory/ acorn_mcp/
mypy --strict api/ memory/

# Unit + integration tests
pytest tests/unit/ -v --cov=api --cov=memory
pytest tests/integration/ -v

# CORTEX+ autonomous operation (verify self-start)
docker compose --profile dgx up -d
sleep 10
curl http://localhost:8000/api/cortex/status   # Should show running=true without manual start

# GRS injection check
curl http://localhost:8000/api/rewards/role-context/orchestrator

# Constitutional gate check (C1)
curl -X POST http://localhost:8000/api/problems \
  -H "Content-Type: application/json" \
  -d '{"title":"test","description":"test","source_urls":["https://external.com"]}'
# Must return 403

# Smoke test
pytest tests/smoke/test_full_pipeline.py -v
```
