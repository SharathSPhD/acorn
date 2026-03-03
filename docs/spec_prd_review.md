<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# review and comment

Both documents are in very strong shape now: the spec cleanly captures *what* OAK is and must achieve, and the PRD gives a realistic, pattern‑ and test‑driven path for *how* to build it. The main risks left are around keeping complexity staged and making sure tests and observability don’t fall behind the ambition.[^1][^2]

## Spec v1.2: comments

- Objectives and principles are now well‑framed as measurable outcomes instead of implementation details, which makes success testable and future‑proof.[^1]
- The new sections on **Self‑Evolution Boundaries** and **Mandatory vs Optional** are excellent; they give clear guardrails on what the system can change on its own and where human review is required, and they prevent over‑scoping v1.[^1]
- The architecture and harness sections (CANOPY/TRUNK/GROVE/ROOTS/SOIL, `oak-harness`, `oak-api-proxy`) are detailed without being hand‑wavy, and the resource caps (`MAX_AGENTS_PER_PROBLEM`, `MAX_CONCURRENT_PROBLEMS`, `MAX_HARNESS_CONTAINERS`) address earlier scaling concerns.[^1]
- The UI canopy description and problem lifecycle read as a coherent story; they’re concrete enough that you can implement a walking skeleton straight from the text.[^1]

Two areas you might still tighten:

- In the harness/proxy section, you now call out risks and disable stall‑based escalation for v1, which is good; consider explicitly stating that the **default RoutingStrategy is `PassthroughStrategy`** and the only way to enable escalation is a config toggle wired in the PRD (to avoid “accidental cleverness”).[^2][^1]
- In Self‑Evolution Boundaries, you could add a simple “max churn” rule for UI (e.g. no more than N new pages per M problems without human prompt review), to avoid a slowly accreting but incoherent canopy.[^1]


## PRD-2: comments

- The **separation of concerns** is crisp: spec defines intent, PRD defines engineering discipline (patterns, TDD, config‑driven behaviour).[^2]
- The **Design Pattern Registry** is unusually explicit and useful; forcing each module to declare `__pattern__` and enforcing it in tests is a clever way to keep architecture honest over time.[^2]
- The Factory (agent assembly) and Strategy (inference routing) examples are concrete and map directly to spec sections; this makes it much easier to keep the codebase aligned with the document.[^2]
- The TDD workflow, test tree layout (unit/integration/contract/smoke/system), and mock hierarchy give a very solid backbone for implementation; this directly addresses reliability and regression risk.[^2]
- Using Redis channels and a consistent event envelope for streams and mailboxes will make debugging and observability far saner.[^2]

A few targeted suggestions:

- For the pattern registry, add 1–2 examples of “anti‑patterns” you explicitly want to avoid (e.g. God objects in the agent engine, or ad‑hoc conditionals for inference routing), so reviewers have something concrete to push back on.[^2]
- In the TDD section, you might define per‑phase **minimum coverage or test counts** (e.g. “Phase 0 must ship with at least one smoke test and one integration test that exercise CSV→app”) to make the exit criteria even more objective.[^2]
- For config‑driven behaviour, consider making a small “config schema” table (key, type, default, phase introduced) to keep track of critical knobs like OAK_MODE, agent caps, escalation strategies, and memory TTLs.[^1][^2]


## Overall pathway

As they stand, the spec and PRD together now describe:

- Clear business/technical objectives and boundaries (what changes autonomously vs via PR vs only by operator).[^1]
- A layered architecture and harness design that is ambitious but implementable in stages.[^1]
- An engineering process (patterns + TDD + explicit test tiers) that, if followed, should give you a robust walking skeleton on DGX, then a safe path to Mac Mini and cloud.[^2][^1]

If you keep enforcing “patterns first, tests first, config over hardcoding” as non‑negotiable, this is a very strong foundation to build OAK with minimal unpleasant surprises.

<div align="center">⁂</div>

[^1]: spec.md

[^2]: PRD-2.md

