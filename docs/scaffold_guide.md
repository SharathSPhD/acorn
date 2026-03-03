<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# prepare the project scaffoldig 1)worktrees 2)Create an agent team to  Spawn teammates based

on @docs/agentGuidelines.md and improvise on it 3)setup for git (ssh is enabled).username is
SharathSPhD...no email..repo is [https://github.com/SharathSPhD/oak.git](https://github.com/SharathSPhD/oak.git) 4)setup other things
like hooks, rules, skills etc (it is also available from earlier) 5)setup project, agent
memories..use skills 6)           suggest all critical things that are needed for claude code to set it up..also it should avoid create mocks, taking shortcuts, synthetic and rushing to claim success (hooks, tdd, rules to rescue?0

Here’s a concise, concrete scaffolding plan tailored to your repo and OAK’s spec/PRD, focused on making Claude Code + agents “real”, not synthetic. I’ll frame it as what should exist and the key rules to enforce.

***

## 1) Git worktrees and local scaffold

Target repo: `git@github.com:SharathSPhD/oak.git` (SSH enabled).[^1]

**Initial clone + branches**

```bash
git clone git@github.com:SharathSPhD/oak.git oak
cd oak

git checkout main

git checkout -b oak/agents
git push -u origin oak/agents

git checkout -b oak/skills
git push -u origin oak/skills

git checkout -b oak/ui
git push -u origin oak/ui

git checkout main
```

**Worktrees (one directory per concern)**[^1]

```bash
mkdir -p ~/oak-workspaces

git worktree add ~/oak-workspaces/agents  oak/agents
git worktree add ~/oak-workspaces/skills  oak/skills
git worktree add ~/oak-workspaces/ui      oak/ui
```

Per‑problem worktrees are created later via `scripts/new-problem.sh p-<uuid>` as already described in spec.[^1]

***

## 2) Agent team definition (using @docs/agentGuidelines.md spirit)

You already have subagents defined in `.claude/agents/*.md` (Orchestrator, Data Engineer, Data Scientist, ML Engineer, Software Architect, Judge, Skill Extractor, Meta Agent). To “spawn teammates” with stronger guidelines:[^1]

**Add / refine @docs/agentGuidelines.md (new file)**

Content should include:

- Shared lifecycle (Template Method you already defined): restore → orient → skill query → execute role work → validate → report → close → save.[^2]
- Behaviour rules:
    - Never fabricate success: if a tool fails, log it and surface a blocker in the mailbox.
    - Never mark a task `complete` unless a Judge PASS exists (and hooks will enforce this).[^1]
    - Prefer using existing skills over writing new code when confidence is high.
    - Discovery first: for new problem types, do a small DISCOVERY pass before heavy modelling.

**Improvements on the existing roles**

You can add two meta‑roles (no new containers, just refinements to prompts):

- **Problem Framer**: behaviour folded into Orchestrator’s system prompt: always create/refresh `PROBLEM.md` with restated goals, success criteria, and open questions before task creation.
- **UX Shaper**: behaviour folded into Software Architect: must maintain a `UX_SPEC.md` that justifies every widget/page in terms of PROBLEM.md goals.

Update each `.claude/agents/*.md` to reference `@docs/agentGuidelines.md` and to:

- Explicitly list allowed tools (MCP servers, file paths, APIs).
- Explicitly list forbidden actions (e.g., DE can’t touch `ui/`; SA can’t modify schema).[^1]

***

## 3) Git setup for Claude Code (SSH, username)

You: `SharathSPhD`, SSH already enabled.

Inside `~/oak`:

```bash
git config user.name "SharathSPhD"
git config user.email ""   # or a placeholder; Git allows empty
git remote -v               # should show git@github.com:SharathSPhD/oak.git
```

For Claude Code inside `oak-harness`:

- Mount `~/.ssh` read‑only if you want agents to push branches/PRs (safer: have them only commit locally and you push).[^2]
- In `.claude/settings.json`, set:

```json
{
  "git": {
    "defaultRemote": "origin",
    "defaultBranch": "main",
    "userName": "SharathSPhD",
    "userEmail": ""
  }
}
```

Keep **push to `main`, `oak/agents`, `oak/skills`, `oak/ui` blocked** by server‑side hooks as in PRD (pre‑receive on GitHub; you already specified the policy).[^2]

***

## 4) Hooks, rules, skills: what must be present

Most of this is already in spec/PRD; the key is to ensure it’s actually wired and loaded.

**Hooks (in `.claude/hooks/`)**[^1]

- `pre-tool-use.sh`:
    - Reads deny patterns from `scripts/deny-patterns.txt` (shared with `tool-proxy.sh`).[^2]
    - Blocks destructive commands (`rm -rf`, `DROP TABLE`, etc.) with exit 2.
- `post-tool-use.sh`:
    - Writes to `agent_telemetry` on every tool call.[^1]
    - Calls `oak-session save` as needed.
- `task-completed.sh`:
    - Blocks task closure if no PASS in `judge_verdicts`.[^1]
    - Triggers Skill Extractor.
- `teammate-idle.sh`:
    - Fires after `OAK_IDLE_TIMEOUT_SECONDS`, injects “you seem idle” prompt; logs to telemetry.[^1]

**Rules**

- Root `CLAUDE.md` must:
    - Point Anthropic env to `http://oak-api-proxy:9000` + `AUTH_TOKEN=ollama`.[^1]
    - Declare: no commits to main; Judge PASS required; no external APIs except proxy.[^1]
- Enforce PRD rules in CI:
    - Test-first requirement (check that new code touches tests).
    - `__pattern__` required in all production modules.[^2]
    - Coverage thresholds and mutation testing as already defined.[^2]

**Skills**

- Ensure `~/oak-workspaces/skills/{permanent,probationary}` exist and are mounted into harness.[^2][^1]
- Seed a couple of **real** skills, not dummies:
    - `etl-csv-ingestion` (you will actually use it in Phase 2).[^1]
    - A simple `basic-eda` skill.

***

## 5) Project + agent memories + skill usage

**Memory repositories**[^2][^1]

- Use the Repository implementations defined in PRD:
    - `PostgresEpisodicMemoryRepository` wired to `episodes` table.
    - `FilesystemSkillRepository` pointing to skill paths.
    - `RedisWorkingMemoryRepository` for per‑agent session data.
- Inject them via `api.dependencies.get_*` as described; do not construct them ad‑hoc.[^2]

**Agent memory behaviour**

- All agents must:
    - Log meaningful events to episodic memory (via EventBus subscriber).
    - Query `oak-skills` MCP before inventing new patterns.[^2][^1]
- Make sure `oak-memory-mcp` and `oak-skills-mcp` are runnable and registered in `.claude/mcp.json`.[^1]

***

## 6) Critical things Claude Code needs (to avoid mocks/shortcuts)

To **force real behaviour and avoid synthetic “it works!”**:

1. **Bootstrap sequence must run**
Use the `scripts/bootstrap.sh` from spec v1.2 (or finalize it) to:
    - Clone repo, set up branches/worktrees.
    - Build `oak-harness` and `oak-api-proxy`.
    - Start base stack (`oak-postgres`, `oak-redis`, `oak-ollama`, `oak-api`, `oak-ui`).[^1]
2. **No agent work before Phase 0 + Phase 1 tests are green**[^2][^1]
    - Phase 0: CSV→DB→static app pipeline, no agents.
    - Phase 1: single Claude Code agent in harness, all harness/proxy contract tests green.
3. **Disable stall‑based escalation by default**
    - `ROUTING_STRATEGY=passthrough`, `STALL_DETECTION_ENABLED=false` until you explicitly turn it on.[^2]
    - This avoids subtle “Claude saved it” illusions.
4. **Test‑driven, no mock‑only success**

- Enforce in CI:
    - No production file without a corresponding test touching its public surface.[^2]
    - No PR without at least one new or modified test when production code changes.
- For system behaviour (problem→app), rely on **system/smoke tests** that hit the live stack, not just unit mocks.[^2]

5. **Hook + state machine guards turned on in all non‑dev runs**

- `judgerequired=true` in any environment where results might be acted upon.[^2]
- Task State Machine always active; `task-completed.sh` always installed.[^2]
- No “dev mode” that bypasses Judge or hooks in normal operation.

6. **Real telemetry + dashboards from day one**

- Ensure `agent_telemetry`, `judge_verdicts`, and core metrics from spec v1.2 are populated.[^1]
- Build a minimal Streamlit telemetry page (or CLI query) that shows:
    - Time per problem.
    - Number of Judge FAILs.
    - Skill reuse vs new skills.
- This makes it hard for agents to “declare victory” when the numbers disagree.

***

If you wire these pieces as above—worktrees, agent team with clear guidelines, Git + hooks, real memory+skills repositories, CI rules enforcing TDD and patterns—you’ll give Claude Code a scaffold where it **can’t** cheat with mocks or shortcuts and where every “success” really means a live problem→app flow completed.

<div align="center">⁂</div>

[^1]: spec.md

[^2]: PRD-2.md

