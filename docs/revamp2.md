<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# revise this...name different from fabric (connect with words from nature)....it should also be workable on dgx spark..it will be initiated there and then ported to mac mini and also experimented on cloud

**OAK** (Orchestrated Agent Kernel) is a self-evolving AI factory inspired by the oak tree—deep-rooted in local compute, branching into limitless agent swarms, and growing stronger with every cycle. It starts on DGX Spark for power users, ports seamlessly to Mac Mini M4, and scales to cloud multi-GPU, using open-source tools and free UI hosting for true flexibility.

## Core Concept

OAK ingests raw problems (data + goals) and forges custom dashboards via dynamic agent collectives that expand freely—no fixed limits, no proprietary lock-in. UI via Streamlit/Plotly Dash on free platforms (Streamlit Cloud, Render, Vercel). Zero third-party chat tools, zero security overhead—simple Docker isolation handles it.

## Architecture Layers

```
┌──────────────────────┐
│ L6: UI CANOPY (Streamlit/Dash) │
│ Free: Streamlit Cloud/Render/Vercel │
│ Submit | Live stream | App gallery │
└──────────┬──────┘
           │ REST/WS
           ▼
┌──────────────────────┐
│ L5: API TRUNK (FastAPI) │
│ /problems /agents /tasks /skills │
└──────────┬──────┘
           ▼
┌──────────────────────┐
│ L4: AGENT GROVE (LangChain/CrewAI) │
│ Orchestrator spawns 1-100+ agents │
│ Roles emerge: Data, ML, Synth... │
│ Coord: Redis queue + async msgs │
└──────────┬──────┘
           ▼
┌──────────────────────┐
│ L3: MODEL CANOPY (Ollama/LM Studio) │
│ Llama3.3, Qwen, Mistral local │
│ Optional: Grok/Claude API escalate │
└──────────┬──────┘
           ▼
┌──────────────────────┐
│ L2: ROOT MEMORY (SQLite/pgvector) │
│ Redis (ephemeral) │
│ Vector DB (sessions) │
│ Skills (JSON/FS index) │
└──────────┬──────┘
           ▼
┌──────────────────────┐
│ L1: HARDWARE SOIL │
│ DGX Spark → Mac Mini M4 → Cloud GPU │
└──────────────────────┘
```


## Hardware Journey

| Stage | Hardware | Tokens/sec | Use Case |
| :-- | :-- | :-- | :-- |
| Init | DGX Spark GB10 | 200+ on 70B | Heavy parallel problems |
| Port | Mac Mini M4 Pro 64GB | 20-50 on 30B | Daily dev/prototyping |
| Scale | RunPod A100 x4 | 500+ concurrent | Production swarms |

All Dockerized—one `docker-compose.yml` adapts via env vars (e.g., `OAK_MODE=dgx|mini|cloud`).

## Key Advantages

| Aspect | Old FORGE | OAK |
| :-- | :-- | :-- |
| Name | Acronym mismatch | Nature: oak tree growth metaphor |
| Hardware | DGX-only | DGX init → Mac Mini → Cloud seamless |
| Agents | Fixed 4 | Unlimited grove—emergent scaling |
| UI | Lovable limits | Streamlit/Dash—free, Git auto-deploy |
| Security | OpenClaw vulns | No harness—Docker + user isolation |
| Portability | Heavy stack | SQLite start, scales to Postgres |

## Problem Lifecycle

1. **Submit**: Streamlit form → API spins orchestrator.
2. **Branch**: N agents (5-100) claim Redis tasks dynamically.
3. **Process**: Parallel ingest/analyze/model/synth in containers.
4. **Prune**: Judge gates → heal/retry or deploy Dash app.
5. **Grow**: Extract skills; UI evolves (new forms via Git push).
6. **Shed**: Old episodic mem to cold storage (90d TTL).

## Self-Evolution Loop

```
Problem solved
↓
Skill Extractor → Probationary library
↓
Reused 2+ problems? → Permanent skills
↓
New UI needs → Auto Git commit → Vercel redeploy
↓
Richer problems → Stronger grove → Repeat
```


## Quickstart by Platform

**DGX Spark (Week 1 init)**:

```
git clone oak-ai
docker compose up -f docker-compose.dgx.yml
streamlit run canopy.py  # share.streamlit.app link
```

**Mac Mini M4 (Week 2 port)**:

```
cp docker-compose.dgx.yml docker-compose.mini.yml
sed -i 's/pgvector/sqlite/' docker-compose.mini.yml
docker compose up
```

**Cloud (Week 3 scale)**:

```
# RunPod: Deploy API to A100 pod
# Vercel: UI from GitHub
OAK_MODE=cloud docker compose up
```


## What Makes OAK New

1. **Living Memory**: Skills persist/learn across 1000+ problems—no reset.
2. **Evolving Interface**: UI grows new branches as capabilities expand.
3. **Rooted Flexibility**: Single codebase spans laptop-to-cluster.
4. **Grove Scaling**: Agents multiply naturally—no artificial limits.

OAK grows where you plant it—from DGX roots to cloud canopy—always open-source, always yours.

