# ACORN Quality Audit Report

**Date:** March 5, 2026  
**Scope:** Post-OAK→ACORN migration quality audit  
**Excluded:** `docs/oak-archive/`, `.git/`

---

## HIGH Severity

### 1. Runtime crash: `settings.oak_network` does not exist

| File | Line | Issue |
|------|------|-------|
| `api/routers/problems.py` | 209, 259 | Uses `settings.oak_network` but `AcornSettings` defines `acorn_network` |

**Impact:** `AttributeError` when starting a problem or spawning an agent. The `/problems/{id}/start` and `/problems/{id}/spawn-agent` endpoints will fail.

**Fix:**
```python
spec.network = settings.acorn_network
```

---

### 2. acorn-kernels-mcp: queries non-existent `skills` table

| File | Line | Issue |
|------|------|-------|
| `acorn_mcp/acorn-kernels-mcp/server.py` | 75, 82 | `find_skills` tool queries `FROM skills` but schema has `kernels` table only |

**Impact:** MCP `find_skills` tool fails with `relation "skills" does not exist` when agents query the kernel library.

**Fix:** Change both queries from `FROM skills` to `FROM kernels`.

---

### 3. acorn-kernels-mcp: `add_skill_use` tool never handled

| File | Line | Issue |
|------|------|-------|
| `acorn_mcp/acorn-kernels-mcp/server.py` | 41, 100 | Tool `add_skill_use` is declared but handler checks `add_kernel_use`. Call falls through to `else` and raises `ValueError` |

**Impact:** Agents cannot record kernel use; `add_skill_use` always fails.

**Fix:** Either (a) rename tool to `add_kernel_use` and update schema to use `kernel_id`, or (b) add handler for `add_skill_use` that maps `skill_id` → `kernel_id` and delegates to kernel logic.

---

### 4. acorn-kernels-mcp: `request_promotion` schema mismatch

| File | Line | Issue |
|------|------|-------|
| `acorn_mcp/acorn-kernels-mcp/server.py` | 57, 113 | Tool inputSchema has `skill_id` but handler expects `kernel_id` |

**Impact:** MCP clients passing `skill_id` will cause `KeyError` when handler accesses `arguments["kernel_id"]`.

**Fix:** Use `arguments.get("kernel_id") or arguments.get("skill_id")` for backward compatibility, or standardize on `kernel_id` in schema.

---

### 5. UI calls wrong API path: `/api/skills` vs `/api/kernels`

| File | Line | Issue |
|------|------|-------|
| `ui-next/src/lib/api.ts` | 222, 225 | `api.skills.list()` and `api.skills.promote()` call `/api/skills` and `/api/skills/{id}/promote` |

**Impact:** Hub kernel gallery and promote actions return 404; router is at `/api/kernels`.

**Fix:** Change to `/api/kernels` and `/api/kernels/{id}/promote`.

---

### 6. seed_skills.sql inserts into non-existent `skills` table

| File | Line | Issue |
|------|------|-------|
| `scripts/seed_skills.sql` | 5–29 | `INSERT INTO skills (...)` but schema has `kernels` table |

**Impact:** `bootstrap.sh` runs this script; seed fails with `relation "skills" does not exist`.

**Fix:** Change to `INSERT INTO kernels (...)` and update column names to match `api/db/schema.sql` (e.g. `kernels` columns).

---

### 7. Test assertions expect `skills` table; code uses `kernels`

| File | Line | Issue |
|------|------|-------|
| `tests/unit/test_skill_repository.py` | 104, 124 | Asserts `"UPDATE skills SET status='permanent'"` and `"UPDATE skills SET status='deprecated'"` |
| `tests/integration/test_skill_extraction_loop.py` | 73 | Asserts `"UPDATE skills SET status='permanent'"` |

**Impact:** Tests fail (3 failures confirmed). CI may be broken or these tests excluded.

**Fix:** Change assertions to `"UPDATE kernels SET status='permanent'"` and `"UPDATE kernels SET status='deprecated'"`.

---

## MEDIUM Severity

### 8. Direct `os.environ` access outside `api/config.py`

| File | Line | Issue |
|------|------|-------|
| `api/ws/stream.py` | 16 | `REDIS_URL = os.environ.get("REDIS_URL", ...)` |
| `acorn_mcp/acorn-kernels-mcp/server.py` | 15–16 | `DATABASE_URL`, `ACORN_KERNEL_PROMO_THRESHOLD` |
| `acorn_mcp/acorn-memory-mcp/server.py` | 15 | `DATABASE_URL` |
| `acorn_mcp/acorn-api-relay/main.py` | 31–42, 68, 75, 84 | Multiple env vars |
| `docker/acorn-harness/scripts/session-state.py` | 20–79 | Multiple env vars |

**Impact:** Violates PRD §1.3 and CLAUDE.md: "api/config.py is the ONLY file that reads os.environ". MCP servers and harness scripts run in separate processes and may need their own config; `api/ws/stream.py` should use `settings.redis_url`.

**Fix:** For `api/ws/stream.py`: `from api.config import settings` and use `settings.redis_url`. For MCP/harness: document exception or introduce shared config module.

---

### 9. Leftover OAK references in scripts

| File | Line | Issue |
|------|------|-------|
| `scripts/cleanup-orphans.sh` | 6 | Filters `name=oak-harness-` but containers are `acorn-harness-` |
| `install.sh` | 2–53 | Multiple OAK references: "OAK Installer", "oak-aio", "oak-data", "oak-ollama", "oak-workspace", ghcr.io/sharathsphd/oak-aio |
| `docker/init-db.sh` | 7 | Message says "OAK schema" instead of "ACORN schema" |

**Impact:** `cleanup-orphans.sh` never removes stopped harness containers. `install.sh` uses old branding and may point to deprecated images.

**Fix:** Update `cleanup-orphans.sh` to `acorn-harness-`. Rebrand `install.sh` to ACORN and update image references if repo moved.

---

### 10. ui-next package-lock.json has `oak-hub`

| File | Line | Issue |
|------|------|-------|
| `ui-next/package-lock.json` | 2, 8 | `"name": "oak-hub"` while `package.json` has `"acorn-hub"` |

**Impact:** Lock file out of sync; minor inconsistency.

**Fix:** Run `npm install` in ui-next to regenerate lock file from package.json.

---

### 11. Agent terminology: SkillRepository vs KernelRepository

| File | Line | Issue |
|------|------|-------|
| `.claude/agents/orchestrator.md` | 14 | "SkillRepository handles that" |
| `.claude/agents/skill-extractor.md` | 3, 10, 68, 83 | "SkillRepository.promote()", "skills/probationary/", "skills/permanent/" |
| `.claude/agents/data-engineer.md` | 45 | "skills/permanent/" |

**Impact:** Agent instructions reference old naming; may cause confusion. Paths `skills/probationary` and `skills/permanent` should be `kernels/probationary` and `kernels/permanent` per CLAUDE.md.

**Fix:** Replace SkillRepository → KernelRepository, skills/ → kernels/ in agent docs.

---

### 12. Role name inconsistency: skill-extractor vs kernel-extractor

| File | Line | Issue |
|------|------|-------|
| `api/routers/agents.py` | 93 | `"skill-extractor": settings.analysis_model` |
| `api/config.py` | 102 | `analysis_roles = {"kernel-extractor", ...}` |
| `docker/acorn-harness/scripts/entrypoint.sh` | 360, 614, 627, 632 | Uses `kernel-extractor` |
| Agent file | `.claude/agents/skill-extractor.md` | `name: skill-extractor` |

**Impact:** Config and entrypoint use `kernel-extractor`; agents API and agent file use `skill-extractor`. Role routing may not match spawned role.

**Fix:** Standardize on `kernel-extractor` (align with kernel terminology) and rename agent file to `kernel-extractor.md`, or keep `skill-extractor` and update config/entrypoint.

---

## LOW Severity

### 13. Config vs PRD.md discrepancies

| PRD Variable | PRD Default | api/config.py | Status |
|--------------|------------|---------------|--------|
| MAX_AGENTS_PER_PROBLEM | 8 (dgx: 10) | 10 | Config has single value; PRD has profile overrides |
| MAX_CONCURRENT_PROBLEMS | 3 (dgx: 5, mini: 1) | 3 | No profile overrides in config |
| MAX_HARNESS_CONTAINERS | 15 (dgx: 20) | 20 | Different default |
| KERNEL_DEPRECATION_THRESHOLD | 0.4 | — | Missing from config |
| ACORN_API_URL | — | — | Not in config (used by clients via env) |
| ORCHESTRATOR_MODEL, RESEARCH_MODEL, etc. | — | — | Model overrides not in config |
| WARDEN_POLL_INTERVAL | 30 | — | In docker-compose only |
| STALE_THRESHOLD_SECONDS | 1800 | — | Not in config |
| KERNEL_PROBATIONARY_PATH | /acorn-workspaces/kernels/... | /workspace/kernels/... | Different base path |

**Impact:** Config may not support all PRD settings; profile-based defaults (dgx/mini/cloud) not implemented in config.

**Fix:** Add missing settings to `AcornSettings`; consider profile-based defaults in `model_validator` based on `acorn_mode`.

---

### 14. memory/skills.py filename vs content

| File | Issue |
|------|-------|
| `memory/skills.py` | Defines `FilesystemKernelRepository` (Kernel, not Skill). Filename suggests legacy. No imports found. |

**Impact:** Misleading filename; possible dead code.

**Fix:** Rename to `memory/filesystem_kernel_repository.py` or remove if unused.

---

### 15. Test file naming and docstrings

| File | Issue |
|------|-------|
| `tests/unit/test_skills_router.py` | Tests kernels router; name suggests skills |
| `tests/unit/test_cached_skills.py` | Tests CachedKernelRepository |
| `tests/unit/test_skill_repository.py` | Tests PostgreSQLKernelRepository |

**Impact:** Naming inconsistency; docstrings reference "skills" where "kernels" is correct.

**Fix:** Rename to `test_kernels_router.py`, `test_cached_kernels.py`, `test_kernel_repository.py` and update docstrings.

---

### 16. Intentional OAK references (no change)

| File | Context |
|------|---------|
| `spec.md` | "extends OAK", "OAK's skills", "no OAK builder" — historical context |
| `PRD.md` | "Kernels replace OAK's skills" — migration note |

These are acceptable as documentation of migration.

---

## Summary

| Severity | Count |
|----------|-------|
| HIGH | 7 |
| MEDIUM | 5 |
| LOW | 4 |

**Recommended order of fixes:**
1. Fix `settings.oak_network` → `settings.acorn_network` (immediate runtime fix)
2. Fix acorn-kernels-mcp (skills→kernels table, tool handlers)
3. Fix ui-next API paths
4. Fix seed_skills.sql
5. Fix test assertions
6. Update scripts (cleanup-orphans, install.sh, init-db.sh)
7. Align agent docs and role naming
8. Address config completeness and os.environ usage
