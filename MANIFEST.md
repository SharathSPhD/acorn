# ACORN — Adaptive Collaborative Orchestration and Reasoning Network

## MANIFEST v1.0 · March 2026

**ACORN** = Adaptive Collaborative Orchestration and Reasoning Network. A self-evolving, general-purpose knowledge-work factory.

---

## PREAMBLE

This document is ACORN's living covenant. It defines what ACORN is, what it serves, how it evolves, and the principles it must never violate. ACORN reads this manifest, identifies gaps between current capability and vision, and evolves through PR-based amendments — not autonomous self-build.

Companion documents:
- **spec.md** — Technical specification, architecture, agent definitions, schema
- **PRD.md** — Implementation rules, configuration, environment variables

The WARDEN daemon is the infra-only component. There is no builder, no cortex. All evolution is gated by human review and merge.

---

## PART I — IDENTITY AND PURPOSE

### 1.1 What ACORN Is

ACORN is a self-evolving, locally-sovereign knowledge-work factory. It accepts raw inputs (goals, documents, datasets, URLs) and produces knowledge artefacts: reports, recommendations, synthesised summaries, BI dashboards, workflow scripts, and deployed apps — without cloud APIs, without data leaving the organisation.

ACORN operates as a team of 9 specialised agents (Orchestrator, Research Analyst, Synthesis Agent, Domain Specialist, Validator, Judge, Kernel Extractor, Interface Agent, Calibration Agent) inside isolated Docker containers (acorn-harness). "Skills" are now **Kernels** — versioned, testable units with Python modules + test suites. Every problem produces a REASONING_TRAIL.md as a first-class output.

### 1.2 What ACORN Serves

**Business domains (9):**

| Domain | Description |
|--------|-------------|
| Sales | Pipeline conversion, funnel analysis, win/loss, opportunity forecasting |
| Pricing | Price elasticity, value-based pricing, competitive benchmarking, margin analysis |
| Marketing | Campaign attribution, ROI, segmentation, reach/frequency, conversion funnel |
| Supply Chain | Demand forecasting, inventory optimisation, supplier performance, lead time |
| Customer | Churn prediction, LTV, NPS, retention cohort, segmentation |
| Finance | P&L variance, cash flow, budgeting, capital allocation, risk metrics |
| Operations | Throughput, capacity utilisation, SLA, bottleneck analysis, process efficiency |
| Human Capital | Headcount, turnover, performance, compensation benchmarking, training ROI |
| Product | Usage analytics, feature adoption, A/B testing, roadmap prioritisation |

**Broader knowledge-work domains:**

| Domain | Description |
|--------|-------------|
| Research Synthesis | Systematic literature review, evidence mapping, meta-analysis |
| Business Intelligence | Cross-domain insight reports, executive briefings, strategic recommendations |
| Document Analysis | Contract review, regulatory compliance scanning, policy comparison |
| Data Engineering | Pipeline design, schema modelling, ETL workflow generation |
| Technical Documentation | Architecture decision records, API docs, user guides |

### 1.3 What ACORN Is Not

- **Not a chatbot.** Output is structured knowledge artefacts, not conversational responses.
- **Not a dashboard tool.** It produces dashboards; it is not one.
- **Not a data warehouse.** It consumes and transforms data; it does not replace storage.
- **Output is:** code that runs, reports that can be validated, insights that can be actioned, and kernels that can be reused. Every output includes a REASONING_TRAIL.md documenting the full decision chain.

---

## PART II — THE EVOLUTION IMPERATIVE

### 2.1 PR-Based Evolution

ACORN does **NOT** have autonomous self-build (no cortex, no builder). Instead:

- **Kernel Extractor** writes to probationary grove after each PASS verdict
- **KernelRepository.promote()** promotes after 2 independent verified uses
- **Calibration Agent** (if enabled) opens deprecation PRs when benchmark drops below 0.4
- All agent prompt amendments, new Hub pages, and judge rule changes require PR + human merge
- **WARDEN** is infra-only (health checks, orphan cleanup, stale problem detection)

### 2.2 Kernel-Driven Learning

Replace "skill library" with **kernel grove**:

- Kernels contain KERNEL.md + Python module + test suite + benchmark
- Lifecycle: probationary → permanent → deprecated (never deleted)
- Orchestrator queries kernel grove for matching patterns before decomposing new problems
- Each kernel has embedding vector for semantic retrieval (768-dim, nomic-embed-text)

### 2.3 Reasoning Trail as Institutional Memory

Every problem produces **REASONING_TRAIL.md** containing:

- Decomposition decisions (why these tasks, why these agents)
- Kernel retrieval decisions (which kernels matched, which were applied)
- Research strategy choices (what was searched, what was found)
- Synthesis approach selections (how findings were combined)
- Uncertainty flags (what we don't know)
- Validation outcomes (what passed, what failed, why)
- Judge verdict chain

### 2.4 Bounds on Evolution

Self-evolution operates within hard bounds:

| Scope | Mechanism |
|-------|-----------|
| **Autonomous** | Kernel promotion after 2 verified uses, agent task plans, telemetry, memory writes |
| **Requires PR + human merge** | Agent prompts, validation rules, new kernel categories, Hub pages, kernel deprecation |
| **Requires operator action** | Schema migrations, API surface changes, Docker Compose changes, resource caps, cloud escalation |
| **No modification** | Security model, isolation boundaries, Part IV of this manifest |

---

## PART III — SOFTWARE ARCHITECTURE

### 3.1 Seven-Layer Stack

```
CANOPY  — Next.js Hub UI (port 8501)
TRUNK   — FastAPI Gateway (port 8000)
GROVE   — Agent Engine (acorn-harness containers)
RELAY   — API Proxy (port 9000)
WARDEN  — Self-healing daemon (no LLM)
ROOTS   — PostgreSQL 16 + pgvector, Redis 7
SOIL    — Hardware (DGX Spark / Mac Mini M4 / Cloud GPU)
```

### 3.2 Design Patterns

| Pattern | Location | Role |
|---------|----------|------|
| Factory | api/factories/agent_factory.py | Model routing per agent role |
| Observer | api/events/bus.py | All events published; telemetry subscribers record |
| Repository | memory/kernel_repository.py, memory/episodic_repository.py | Kernel grove; episodic memory |
| StateMachine | api/state_machines/task.py | Task lifecycle |
| TemplateMethod | api/lifecycle/agent_lifecycle.py | Abstract agent lifecycle |
| Strategy | acorn_mcp/acorn-api-relay/strategies.py | Routing strategy |
| ChainOfResponsibility | memory/validation_chain.py | Kernel validation |
| Decorator | memory/cached_kernels.py | Kernel caching |
| Configuration | api/config.py (AcornSettings) | All env vars centralized |

### 3.3 Data Science Stack

Required libraries for the acorn-harness container:

| Category | Libraries |
|----------|-----------|
| **Statistical foundation** | numpy, scipy, statsmodels, pandas, polars |
| **Machine learning** | sklearn, xgboost, lightgbm, catboost, shap |
| **Time series** | statsforecast, neuralforecast, mlforecast, prophet |
| **Complexity** | pymc, networkx, pyod, optuna |
| **Geospatial** | geopandas, ortools |
| **Output** | plotly, matplotlib, jinja2, tabulate |
| **Data quality** | great_expectations, pandera |

### 3.4 Domain Knowledge Requirements

For each of the 9 business domains, agents must be able to implement these core analytical concepts:

| Domain | Core Concepts |
|--------|---------------|
| **Sales** | Pipeline conversion rates, funnel stage analysis, win/loss decomposition, opportunity forecasting, territory optimisation |
| **Pricing** | Price elasticity estimation, value-based pricing models, competitive benchmarking, discount optimisation, margin analysis |
| **Marketing** | Campaign attribution, ROI by channel, customer segmentation, reach/frequency, conversion funnel analysis |
| **Supply Chain** | Demand forecasting, inventory optimisation, supplier performance scoring, lead time analysis, logistics cost allocation |
| **Customer** | Churn prediction, LTV modelling, NPS analysis, retention cohort analysis, customer segmentation |
| **Finance** | P&L variance analysis, cash flow modelling, budgeting vs actuals, capital allocation, risk metrics (VaR, Sharpe) |
| **Operations** | Throughput metrics, capacity utilisation, SLA monitoring, bottleneck analysis, process efficiency |
| **Human Capital** | Headcount planning, turnover analysis, performance calibration, compensation benchmarking, training ROI |
| **Product** | Usage analytics, feature adoption curves, A/B test analysis, roadmap prioritisation, technical debt quantification |

---

## PART IV — PRINCIPLES (IMMUTABLE)

These principles may not be amended without explicit operator decision and manifest version bump.

| ID | Principle | Description |
|----|-----------|-------------|
| **P1** | Local Sovereignty | All problem data, agent memory, kernels, and reasoning traces remain on operator-owned hardware. Cloud escalation is optional and stateless. |
| **P2** | Bounded Autonomy | CORTEX+ cognitive kernel drives self-directed improvement within constitutional gates (GRS Layer 4). Evolution is gated by manifest reconciliation — the system can only pursue objectives that close gaps between desired state (manifest_domains.json) and actual capability. Operator halt via `POST /api/cortex/stop` or Hub UI at any time. |
| **P3** | Verifiable Truth | Kernel grove is ground truth. Every kernel is testable. Every output is auditable via REASONING_TRAIL.md. |
| **P4** | Graceful Degradation | When local models stall or fail, the system degrades gracefully. No silent failures. Escalation is logged. |
| **P5** | Transparent Change | Reasoning trails + git history. Every significant decision is traceable. |
| **P6** | No Hallucinated Credentials | Agents never fabricate citations, credentials, or data. All claims trace to RESEARCH.md or validated sources. |
| **P7** | Resource Respect | Resource caps are enforced. No unbounded spawning. Operator controls hardware allocation. |

---

## PART V — SELF-ASSESSMENT METRICS

| Metric | Description | Target |
|--------|-------------|--------|
| **Kernel grove coverage** | Domains with ≥3 permanent kernels | Expand over time |
| **Judge verdict pass rate** | % of problems receiving PASS | Monitor trend |
| **Kernel promotion rate** | Probationary → permanent per week | Sustainable growth |
| **Mean time to solution** | Median wall-clock from submit to complete | Decrease with kernel reuse |
| **Reasoning trail completeness** | % of problems with full REASONING_TRAIL.md | 100% |
| **WebSocket live streaming coverage** | % of agent events streamed to Hub | 100% |

---

*End of MANIFEST.md v1.0*
