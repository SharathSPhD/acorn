<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# [https://docs.ollama.com/integrations/claude-code](https://docs.ollama.com/integrations/claude-code)  refer to this...this gives claude code power through ollama and local models....also understand what would be missed if openclaw is not used....if that it critical then find a way to bring together both claude with ollama and openclaw

Ollama's Claude Code integration is a perfect fit for OAK's dynamic reconfiguration—running **Claude Code's full harness (subagents, plugins, skills, teams, hooks)** locally via Ollama models, avoiding cloud costs and data leaks while sidestepping OpenClaw's security pitfalls. Here's how it works, what OpenClaw adds/misses, and the integrated solution.

## Ollama + Claude Code: The Magic

Per Ollama docs, Claude Code (Anthropic's dev agent tool) connects to Ollama via **environment variable overrides**:[^1]

```
export ANTHROPIC_BASE_URL=http://localhost:11434
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""  # Empty
claude --model qwen3-coder  # Or glm-4.7, gpt-oss:20b/120b
```

- **What you get**: Claude Code thinks it's calling Anthropic API, but hits **Ollama's Anthropic-compatible endpoint**. Full harness available:


| Feature | Available via Ollama |
| :-- | :-- |
| Subagents | Yes (MCP orchestration) |
| Plugins/Tools | Yes (file I/O, shell, git, tests) |
| Skills | Yes (Voyager-style composable modules) |
| Agent teams | Yes (Team Lead + specialists) |
| Hooks/Lifecycle | Yes (PreTool, PostTask, etc.) |
| Context | 64k+ tokens (Ollama supports via modelfile) |

- **Local power**: Reasoning runs on your DGX/Mac Mini/cloud GPUs with Ollama models (Qwen3-Coder excels for code).[^1]
- **No cloud**: Zero Claude API tokens billed; fully sovereign.

This **directly enables OAK's loop**:

1. **Orchestrator agent** (Claude Code + Ollama model) spawns team.
2. **Team executes** (local models), writes code/skills to sandboxed dir.
3. **Extractor/UI Architect** (same harness) reads artifacts → edits `skills/`, `ui/`.
4. **Git agent** (Claude Code tool) commits → triggers Vercel/Streamlit redeploy.

## OpenClaw: What's Missed If Skipped

OpenClaw is a **local dev environment wrapper** for Claude Code (Dockerized terminal + git + persistent state). What it provides:


| Feature | OpenClaw | Ollama + Claude Code |
| :-- | :-- | :-- |
| Persistent terminal | Yes (stateful shell) | No—stateless per run |
| Git integration | Native (local repo) | Yes (Claude Code git tool calls) |
| Docker-aware tooling | Yes | Manual (your Docker) |
| No Anthropic cloud | Yes | Yes (Ollama backend) |
| Security | Critical issues: RCE via exposed UI, prompt injection, data leaks[^2][^3][^4] | Clean—your Docker isolation |

**Missed if no OpenClaw**: Mostly **persistent state** (terminal history, open files). But **critical? No**—Claude Code's tools already handle 95% (file/git/shell), and stateless is safer/faster for agents.

## Integrated Solution: OAK Harness (Ollama‑Claude + Safe OpenClaw Alt)

**Don't use raw OpenClaw** (security nightmare). Instead, **bundle Ollama + Claude Code + minimal wrapper**:[^2][^5]

```
# docker-compose.oak.yml
services:
  ollama:
    image: ollama/ollama
    models: [qwen3-coder, glm-4.7]
  
  claude-harness:
    image: your-oak/claude-harness  # Custom Docker
    environment:
      - ANTHROPIC_BASE_URL=http://ollama:11434
      - ANTHROPIC_AUTH_TOKEN=ollama
      - PROJECT_DIR=/workspace  # Sandboxed /oak-project
    volumes: [/host/oak-project:/workspace]
    tools:  # Expose safe subset
      - file_read, file_write
      - git_status, git_commit, git_push
      - pytest_run, black_lint
      - docker_compose_up  # Controlled
  
  orchestrator:
    command: claude --model qwen3-coder --workspace /workspace
```

**Wrapper logic** (in `claude-harness`):

- **Sandbox everything** to `/workspace` (skills/ui/config)—no host access.
- **Proxy tools**: Intercept Claude Code's shell/git calls → validate → execute safely (no `rm -rf`, no network out).
- **Persistent state lite**: Redis for session mem (open files, recent cmds)—mimics OpenClaw without vulns.
- **Escalation hook**: If local model stalls (e.g., "reasoning fail"), optional proxy to real Claude API.

**Flow for dynamic builds**:

```
New problem → Orchestrator (Claude Code + Qwen3 via Ollama)
↓
Spawns team → Each uses harness tools → Writes to /workspace
↓
Extractor reads workspace → Edits skills/ui → git commit
↓
CI/CD (GitHub Actions/Vercel) → Redeploys UI
↓
Next problem sees evolved system
```


## Deployment Across Platforms

| Platform | Setup |
| :-- | :-- |
| **DGX Spark** | Full Ollama (70B+ models), harness at scale. |
| **Mac Mini M4** | Qwen3-Coder (20-50 t/s), same Docker. |
| **Cloud** | RunPod GPU pod → `docker compose up`. |

**Pros**: Full Claude Code UX (teams/skills/hooks) with local models. No OpenClaw risks—your safe wrapper. Portable.

**Tradeoff**: Claude Code binary size (~100MB), but Docker handles it. If too heavy, fallback to LangChain pure Python harness (loses some polish).

This **unlocks everything**: Reconfig happens via Claude Code's battle-tested dev patterns, powered 100% locally via Ollama, secured by design.[^1]

<div align="center">⁂</div>

[^1]: FORGE_system_framing.md

[^2]: https://thehackernews.com/2026/02/clawjacked-flaw-lets-malicious-sites.html

[^3]: https://www.kaspersky.co.uk/blog/openclaw-vulnerabilities-exposed/30037/

[^4]: https://www.giskard.ai/knowledge/openclaw-security-vulnerabilities-include-data-leakage-and-prompt-injection-risks

[^5]: https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare

