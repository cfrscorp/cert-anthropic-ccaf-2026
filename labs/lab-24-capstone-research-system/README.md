# L24 — Capstone: Multi-Agent Research System

| | |
|---|---|
| **Scenario / Exercise** | S3 (Multi-Agent Research System) · Exercise 4 |
| **Domains** | 1 — Agentic Architecture & Orchestration · 2 — Tool Design & MCP Integration · 5 — Context Management & Reliability |
| **Difficulty** | 9 / 10 |
| **Estimated effort** | 3:30 |
| **Prerequisites** | L19, L20 |

## Objective

Build the **capstone** research system from Scenario 3: a **coordinator** agent
that delegates to specialized subagents — `web_search`, `doc_analysis`,
`synthesis`, `report` — to produce a comprehensive, **cited** report on a broad
topic. This lab integrates every multi-agent idea the exam tests, and each design
choice maps to a Sample Question's correct answer:

- **Broad, covering decomposition** (Sample Q7): partition a topic so subagents
  cover *all* its domains, not one familiar corner.
- **Parallel spawning with isolated context** (Task 1.3): emit multiple `Task`
  calls in a single turn; pass each subagent the **complete** prior findings in
  its prompt because subagents do not inherit coordinator memory.
- **Scoped tools** (Sample Q9): give synthesis a narrow `verify_fact` tool for
  the 85% simple-lookup case; route complex verifications back through the
  coordinator.
- **Structured error propagation** (Sample Q8): on a subagent timeout, propagate
  failure type + attempted query + partial results + alternatives, and *proceed*
  with partial results plus coverage-gap annotations.
- **Provenance & conflict handling** (Task 5.6): preserve every claim→source
  mapping through synthesis, and keep conflicting statistics with attribution +
  dates rather than picking one.

## Background

Hub-and-spoke: the coordinator is the hub; all inter-agent communication,
delegation, and error handling flow through it.

```
                         ┌───────────────────────────┐
                         │        COORDINATOR         │
                         │  allowed_tools: ["Task"]   │
                         │  • partition_scope         │
                         │  • select_subagents        │
                         │  • spawn_parallel (1 turn) │
                         │  • build_subagent_prompt   │
                         │  • error recovery          │
                         └───────────────────────────┘
              Task │            Task │            Task │      (parallel: multiple
                   ▼                 ▼                 ▼        Task calls, one turn)
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │  web_search    │ │  doc_analysis  │ │   synthesis     │
        │ tools:         │ │ tools:         │ │ tools:          │
        │  web_search    │ │  load_document │ │  verify_fact ◄──┼─ scoped: simple
        │  record_find.. │ │  extract..     │ │  (only!)        │  lookups only;
        └───────┬────────┘ └───────┬────────┘ └───────┬─────────┘  complex → back
                │ findings         │ findings         │            through coord.
                │ (claim+source+   │                  ▼
                │  date)           │          ┌────────────────┐
                └──────────────────┴────────► │     report     │
                     merged, provenance       │ tables/prose/  │
                     preserved, conflicts     │ lists + gaps   │
                     annotated                └────────────────┘
```

Each subagent runs with **isolated context**. Everything it needs — goals,
assigned facet, and any **complete prior findings** — must be written into its
prompt. Findings are **structured** (claim, value, excerpt, `source{name,url,date}`)
so attribution and temporal context survive all the way to the report.

## Tasks

Edit the four modules in `starter/`. The public API is fixed by
`solution/` — keep the same names and signatures.

### Task A — `agents.py` (registry & tools)
1. `build_agent_registry()` returns the five agents. The **coordinator's**
   `allowed_tools` **must include `"Task"`** (Task 1.3). The **synthesis** agent's
   `allowed_tools` is **`("verify_fact",)` only** — not the search toolset (Task 2.3).
2. Implement `task_tool_schema`, `record_findings_schema`, `verify_fact_schema`.
   Write system prompts that state **goals and quality criteria**, not step-by-step
   procedures.

### Task B — `coordinator.py` (decompose, select, spawn, pass context)
3. `expected_facets` / `partition_scope`: decompose a broad topic across **all**
   its facets. For "impact of AI on creative industries" that means *visual arts,
   music, writing, film* — the Sample Q7 failure was covering only visual arts.
4. `repair_coverage`: given a too-narrow proposal, add partitions for the missing
   facets (the iterative-refinement fix for Q7).
5. `select_subagents`: choose subagents **dynamically** (doc_analysis only when
   documents are in scope) — don't always run the full pipeline.
6. `build_subagent_prompt`: embed the **complete** prior findings **verbatim**
   (never summarized) — subagents don't inherit context.
7. `spawn_parallel`: make **one** `client.messages.create` call whose response
   carries **multiple** `Task` blocks (parallel = one turn, many Task calls).

### Task C — `errors.py` (structured propagation)
8. `build_error_context` / `handle_timeout`: package failure type, attempted
   query, partial results, and alternatives (Sample Q8-A).
9. `classify_result`: distinguish `access_failure` from `empty_success` — never
   report a timeout as a successful empty result (Q8-C anti-pattern).

### Task D — `synthesis.py` (provenance, conflicts, verify_fact)
10. `merge_claims`: flatten findings while **preserving each claim's source**.
11. `annotate_conflict`: when sources disagree on a `metric`, **keep both** values
    with attribution + dates.
12. `render_by_type`: statistics → table, news → prose, technical → list.
13. `classify_verification` / `verify`: simple lookups use the scoped
    `verify_fact` tool (one call, forced tool choice); complex ones route back
    through the coordinator **without** calling `verify_fact` (Sample Q9-A).

### Task E — `coordinator.run_research` (integrate)
14. Wire it together: `partition_scope → select_subagents → spawn_parallel → run
    each subagent → synthesize`. On a subagent timeout, **proceed** with partial
    results and let the failed facet become a **coverage gap** in the report.

The `client` is injected everywhere — never construct `anthropic.Anthropic()`.

## Deliverables

- `starter/agents.py`, `coordinator.py`, `synthesis.py`, `errors.py` fully
  implemented (matching the public API in `solution/`).
- All tests in `tests/test_lab24.py` passing against your `starter/`.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-24-capstone-research-system                    # your work (starter/) — green when done
LAB_TARGET=solution uv run pytest lab-24-capstone-research-system # reference — always green
```

The suite asserts: the coordinator has `Task` in `allowed_tools`;
`partition_scope("impact of AI on creative industries")` covers music/writing/film
(not only visual arts); `spawn_parallel` emits >1 `Task` in one turn;
`build_subagent_prompt` embeds the **full** prior findings; a simulated timeout
yields structured error context and `run_research` proceeds with partial results
+ a coverage gap; `merge_claims` preserves each claim's source; `annotate_conflict`
keeps both values with attribution + dates; and synthesis's scoped `verify_fact`
path handles simple lookups while complex cases route to the coordinator.

## Stretch goals

- **Iterative refinement loop** (Task 1.2): after synthesis, have the coordinator
  detect coverage gaps, re-delegate targeted queries to `web_search`/`doc_analysis`,
  and re-synthesize until coverage is sufficient.
- **Local recovery before propagation** (Task 5.3): retry a transient timeout once
  inside `run_subagent` (narrower query) before propagating structured error
  context.
- **Crash-recovery manifest** (Task 5.4): export each subagent's findings to a
  known location and have `run_research` resume from a manifest.
- **Fork-based exploration** (Task 1.3/1.7): run two synthesis strategies from the
  same merged findings and compare outputs.
