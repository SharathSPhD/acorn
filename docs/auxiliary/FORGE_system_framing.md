# FORGE
### *Federated Orchestration of Reasoning, Generation and Evolution*

> A continuously self-improving software factory that assembles specialist agent teams,  
> ingests raw problems, builds tailored solutions, and grows wiser with every problem it solves.

---

## I. The Concept

Traditional software is a fixed answer to a known question. FORGE is a machine that generates new answers to any question — and gets faster and better at doing so with every question it sees.

Three research documents converge on one system:

- **gemini_research1.txt** defines the agent team topology, coordination primitives, tripartite memory, and Voyager skill library pattern
- **perplexity_research1.md** frames the dynamic team assembly model and Lovable as the self-rebuilding application surface
- **perplixity_research2.md** grounds everything in sovereign local infrastructure — DGX Spark as the AI core, Ollama for local model runtime, OpenClaw as the local dev harness, Lovable as the thin frontend calling DGX APIs

Together they describe a system with a **body** (DGX Spark), **memory** (tripartite persistence), **hands** (agent teams), and **face** (Lovable Hub). The metaphor of a forge is exact: raw material goes in, heat and pressure are applied by specialist agents, something useful comes out — and with each firing, the forge itself becomes more capable.

---

## II. Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: LOVABLE HUB  (cloud — lovable.dev + Supabase)         │
│  Mission Control UI · Problem Submission · Solution Gallery      │
│  Hub self-rebuilds via GitHub PR + human approval               │
└───────────────────────────┬─────────────────────────────────────┘
                            │  REST + WebSocket API calls
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: DGX SPARK API SURFACE  (Docker — FastAPI/uvicorn)     │
│  /api/problems   /api/agents/status   /api/skills               │
│  /api/tasks   /api/telemetry   WS /stream/agents/:id            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  LAYER 4: AGENT TEAM ENGINE  (Claude Code + OpenClaw harness)   │
│                                                                  │
│  Team Lead (orchestrator)                                        │
│  ├── Data Engineer      → ETL, schema inference, migrations      │
│  ├── Data Scientist     → EDA, embeddings, statistical analysis  │
│  ├── ML Engineer        → model selection, MLOps, inference      │
│  └── Software Architect → solution synthesis, Lovable API call   │
│                                                                  │
│  Coordination: Shared Task List (DB) + Mailbox (peer messages)   │
│  Quality Gates: Judge-Agent · Try-Heal-Retry · Lifecycle Hooks   │
│  Meta-Agent: telemetry analysis, prompt evolution                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  LAYER 3: LOCAL MODEL RUNTIME  (Ollama + Anthropic-compat API)   │
│  Llama-3.3-70B · DeepSeek-V3 · Qwen2.5-Coder                   │
│  Anthropic-compatible endpoint → Claude Code SDK works natively  │
│  Hybrid: local models for routine tasks, Claude API for complex  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  LAYER 2: PERSISTENCE LAYER  (Docker — PostgreSQL + pgvector)    │
│                                                                  │
│  L1 Working Memory  → Redis (session cache, ephemeral)           │
│  L2 Episodic Memory → PostgreSQL + pgvector (semantic retrieval) │
│  L3 Procedural      → SKILL.md filesystem + PostgreSQL index     │
│                                                                  │
│  Task State: tasks table + messages table (Mailbox)              │
│  Problem Data: ingested raw data, transformed tables, embeddings │
│  Telemetry: agent_telemetry table                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  LAYER 1: HARDWARE CORE  (NVIDIA DGX Spark)                      │
│  GB10 Grace Blackwell · 128GB unified memory · ~1 PFLOP          │
│  All layers run as Docker containers on this single node         │
└─────────────────────────────────────────────────────────────────┘
```

### Orchestration Boundary (hard rule)
> **DGX Spark** owns all compute, coordination logic, agent execution, and data.  
> **Lovable Hub** owns all presentation, human interaction, and solution surfacing.  
> Lovable calls DGX APIs only — no split orchestration. Lovable's Supabase holds only auth state and solution metadata (links, names, timestamps). No problem data touches the cloud.

---

## III. The Three Documents → One System

| Research thread | What it contributes to FORGE |
|---|---|
| Gemini (gemini_research1.txt) | Agent topology, memory layers, Voyager skill library, self-healing loops, lifecycle hooks |
| Perplexity 1 (research1.md) | Dynamic team assembly per problem, Lovable as self-rebuilding surface, Hub + Spokes pattern |
| Perplexity 2 (perplixity_research2.md) | DGX Spark as sovereign core, Ollama/Anthropic-compat endpoint, OpenClaw harness, Lovable as thin API consumer |

The synthesis resolves a tension present across all three: they each treat Lovable as both "coordinator" and "frontend." FORGE resolves this cleanly — Lovable is the face, DGX Spark is the brain.

---

## IV. Data Topology

| Data Type | Lives On | Store | Why |
|---|---|---|---|
| Problem data (raw CSV, TXT, DB) | DGX Spark | PostgreSQL | Sensitive; never leaves the node |
| Agent episodic memory | DGX Spark | PostgreSQL + pgvector | Semantic retrieval across sessions |
| Skill library | DGX Spark | Filesystem + PostgreSQL index | Code-as-memory (Voyager pattern) |
| Working context | DGX Spark | Redis | Fast ephemeral session state |
| Task list + Mailbox | DGX Spark | PostgreSQL | Coordination state |
| Telemetry | DGX Spark | PostgreSQL | Meta-agent analysis |
| User auth + sessions | Lovable Cloud | Supabase | Standard cloud auth |
| Solution history | Lovable Cloud | Supabase | Links to deployed solution apps |
| Solution source code | GitHub | Git repository | Bridge between DGX agents and Lovable Cloud |
| Deployed solution apps | Lovable Cloud | Lovable project instances | One per problem (the "Spokes") |

---

## V. The Problem Lifecycle (end-to-end)

A single problem traversing FORGE:

```
1. ARRIVAL
   User uploads dataset + describes problem via Lovable Hub
   → Lovable calls POST /api/problems on DGX Spark
   → Problem ID returned, WebSocket stream opened for live activity

2. ASSEMBLY
   Team Lead spawns 4 specialist agents in isolated contexts
   → Decomposes problem into tasks (JSON, stored in PostgreSQL tasks table)
   → Tasks are topologically ordered (schema task blocks dashboard task)
   → Agents self-claim tasks with file locking to prevent races

3. INGESTION (Data Engineer)
   → Profiles raw files: column types, delimiters, anomalies, nulls
   → Generates DDL, creates PostgreSQL tables
   → Late-binding schema: minimal viable structure first, evolve as needed
   → Messages Data Scientist via Mailbox if statistical profiling needed

4. ANALYSIS (Data Scientist)
   → EDA: distributions, correlations, outliers, semantic clusters
   → Generates pgvector embeddings for unstructured text data
   → Reports findings to Mailbox; ML Engineer and Architect read them

5. MODELING (ML Engineer)
   → Selects algorithm family based on Data Scientist's analysis
   → Checks Skill Library first: "time series anomaly" skill → retrieved
   → If novel: reasons from scratch, adapts, produces solution code
   → Uses local Ollama endpoint for routine scripting; escalates to Claude API for complex decisions

6. SYNTHESIS (Software Architect)
   → Assembles all outputs into a structured Lovable prompt
   → Prompt specifies: UI components, data models, API endpoints, auth flows, visualizations
   → Fires Lovable Build-with-URL API → new solution-specific Lovable project created
   → Commits solution code to GitHub (synced repo)

7. QUALITY GATE
   → Judge-Agent validates: linting, security scan, schema consistency, test pass
   → If fail: routes back to responsible agent with diagnostic context
   → If pass: TaskCompleted hook fires, task closed

8. DELIVERY
   → Lovable Cloud deploys solution app to live URL
   → Solution URL + summary written to Supabase via DGX Spark
   → Lovable Hub shows user: "Your solution is ready" with link
   → WebSocket stream closes

9. LEARNING (post-delivery, async)
   → Skill extraction: identify reusable patterns from this problem
   → New skills enter "probationary library" (not permanent yet)
   → Episodic memory updated with: problem type, approach, outcome, errors
   → Telemetry logged: tool usage, latency per agent, context window consumption
```

---

## VI. The Self-Evolution Loop

This is what makes FORGE genuinely different from a pipeline.

```
Problem solved
    ↓
Skill Extractor (Meta-Agent) identifies reusable patterns
    ↓
Candidate skills enter PROBATIONARY LIBRARY
    ↓
[Used successfully in 2+ independent problems?]
    ├── YES → Promoted to PERMANENT SKILL LIBRARY
    └── NO  → Stays probationary; failure context annotated
    ↓
PERMANENT SKILLS change what agents can do next time
    ↓
New capabilities require new Hub UI controls
    ↓
Software Architect agent generates Hub PR (React components, Edge Functions)
    ↓
[Human reviews and approves PR in GitHub]
    ↓
Lovable Cloud detects merge → auto-redeploys Hub
    ↓
Users see a more capable Hub than before
    ↓
More powerful problems can now be submitted → richer solutions → newer skills
    ↓
[Cycle continues]
```

### Memory TTL and Deprecation
Episodic memories are scored for recency × relevance. Memories older than 90 days with zero retrieval hits are demoted to "cold archive" — still queryable but excluded from default retrieval. Skills unused for 180 days are flagged for review, not deleted. No automatic deletion: failures are as valuable as successes for avoiding repeat mistakes.

---

## VII. Inference Tiering Policy

*Explicit routing rules — not "Team Lead decides."*

| Task Type | Model Tier | Rationale |
|---|---|---|
| ETL scripting, schema DDL | Ollama local (Qwen2.5-Coder 32B) | Routine, structured, fast |
| Statistical analysis, EDA | Ollama local (Llama-3.3-70B) | Well-covered in open-weight training |
| Standard ML algorithm setup | Ollama local (DeepSeek-V3) | Proven patterns in training data |
| Cross-domain synthesis | Claude API (Sonnet) | Novel reasoning required |
| Final software architecture | Claude API (Sonnet) | High-consequence, benefits from strongest model |
| Meta-agent prompt evolution | Claude API (Haiku) | Frequent, low-cost, structured output |
| Judge-Agent validation | Ollama local (Llama-3.3-70B) | Deterministic checks, fast |
| Emergency escalation | Claude API (Opus) | When Sonnet fails twice on same task |

Fallback rule: if Claude API is unavailable (network, rate limit), the system degrades gracefully to Ollama for all tiers and logs the degradation. No task blocks on API availability.

---

## VIII. Hub Architecture — Hub vs. Spokes

FORGE produces two kinds of Lovable apps:

**The Hub** (one, persistent, evolves over time)
- The control tower: problem submission, agent status, task list view, skill library catalog, telemetry dashboard
- Lives at a permanent URL
- Self-rebuilds via human-approved GitHub PRs from agent-generated code
- Backed by Supabase for auth and solution history

**The Spokes** (one per problem, standalone, permanent)
- Each problem generates a bespoke solution app via Lovable Build-with-URL
- Tailored UI exactly to the problem: a time-series dashboard for equipment data, a segmentation tool for customer data, an anomaly explorer for sensor streams
- Lives at its own URL, accessible from the Hub's solution gallery
- Can be shared, embedded, or exported independently

The Hub is the factory control room. The Spokes are the products.

---

## IX. OpenClaw Integration

OpenClaw provides a fully local development environment with persistent terminal state, git integration, and Docker-aware tooling — functioning as a Claude Code harness that doesn't require Anthropic Cloud for its execution environment. In FORGE:

- OpenClaw runs on DGX Spark as a Docker container
- Provides the agent-accessible file system, shell execution, and local git operations
- Claude Code's MCP, skills, subagents, and hooks work within OpenClaw's harness
- The Ollama endpoint is configured as the inference backend via the `ANTHROPIC_BASE_URL` environment variable override

OpenClaw is the most experimental component. FORGE degrades gracefully without it — Claude Code against Ollama directly is the fallback, losing local git integration and persistent terminal state but retaining all agent team and memory capabilities.

---

## X. Known Challenges (honest)

**Network exposure**: DGX Spark runs locally; Lovable is a cloud app. Exposing DGX APIs securely requires either a static IP with TLS termination, a VPN tunnel, or a reverse proxy (Cloudflare Tunnel is the simplest). This is a real infrastructure decision, not a footnote.

**Lovable streaming limits**: Supabase Edge Functions (Deno runtime) have cold-start latency and execution time limits. Real-time agent streaming should use a dedicated WebSocket server on DGX Spark (FastAPI + websockets), not Supabase realtime.

**Solution app proliferation**: Every problem creates a new Lovable project. Lovable has project limits per account. FORGE needs a project lifecycle policy: archive solutions older than N days or consolidate similar problems into evolving solution apps rather than always spawning new ones.

**Skill library noise accumulation**: Addressed by the probationary system, but still requires periodic human curation — especially early, before enough problems have been solved to establish signal vs. noise separation.

**Context window management**: Each teammate has an isolated context window, but complex problems still risk exceeding limits. The Mailbox pattern helps, but the Software Architect agent (which synthesizes all outputs) can accumulate very large contexts. Chunked synthesis with explicit summarization hooks is needed for large problems.

---

## XI. Implementation Roadmap

**Phase 0 — Infrastructure Foundation (Week 1-2)**
- Docker Compose on DGX Spark: PostgreSQL + pgvector, Redis, Ollama with Llama-3.3-70B + Qwen2.5-Coder
- FastAPI server exposing core API endpoints
- Verify Ollama Anthropic-compatible API endpoint works with Claude Code SDK
- Basic Lovable Hub: problem submission form calling DGX API, status display

**Phase 1 — Agent Team Core (Week 3-4)**
- Claude Code agent teams: Team Lead + 4 specialist agents
- Shared Task List in PostgreSQL, Mailbox messaging
- Data Engineer agent: CSV ingestion, schema inference, PostgreSQL tables
- Data Scientist agent: basic EDA, pgvector embeddings
- Judge-Agent: linting + schema validation gate

**Phase 2 — Memory and Skills (Week 5-6)**
- L2 Episodic memory: episode storage + pgvector retrieval
- L3 Skill library: filesystem + PostgreSQL index, probationary system
- Skill extraction after each problem cycle
- Meta-Agent: telemetry logging + basic prompt optimization

**Phase 3 — Solution Generation (Week 7-8)**
- Software Architect agent: structured prompt generation
- Lovable Build-with-URL API integration: first programmatic Spoke creation
- GitHub sync: agent-generated code commits trigger Lovable Hub redeploys
- Human-review PR workflow for Hub evolution

**Phase 4 — Self-Healing and Polish (Week 9-10)**
- Try-Heal-Retry loop with diagnostic agent
- Lifecycle hooks: PreToolUse, TaskCompleted, TeammateIdle
- Inference tiering policy fully implemented with Claude API escalation
- OpenClaw integration (if available)
- WebSocket streaming to Lovable Hub for live agent activity view

---

## XII. What Makes FORGE Genuinely New

**Not just "Claude Code + Lovable + DGX"** — FORGE's novelty comes from three things working together:

1. **Persistent learning across problems.** Most agent systems solve a problem and forget. FORGE's Voyager-pattern skill library means the system literally knows more after every problem than before. The 50th data engineering task runs faster and better than the first not because of fine-tuning but because the system has compiled executable knowledge.

2. **The self-rebuilding surface.** The UI you use to submit problems evolves as the system learns new capabilities. When FORGE solves its first time-series forecasting problem, the Hub grows a "Forecasting" section. When it solves its first geospatial problem, a map view appears. The interface reflects what the system has become — not what it was designed to be at launch.

3. **Sovereign compute.** The agent team's memory, skills, and problem data live on hardware you own. No learned patterns leave the DGX Spark. The system's growing intelligence is yours — not shared with a cloud provider's training runs, not reset by a platform update, not subject to terms of service changes. The system grows in service of your specific domain vocabulary and problem types.

These three properties together create something that hasn't existed: a software factory that improves itself, builds its own interface, and runs on hardware you control.

---

*Document generated by FORGE system design process using sequential thinking + actor-critic methodology.*  
*Synthesized from: gemini_research1.txt, perplexity_research1.md, perplixity_research2.md*
