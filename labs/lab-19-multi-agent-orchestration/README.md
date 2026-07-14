# L19 — Multi-Agent Coordinator–Subagent Orchestration

| | |
|---|---|
| **Task statements** | 1.2 — Orchestrate multi-agent systems with coordinator-subagent patterns · 1.3 — Configure subagent invocation, context passing, and spawning |
| **Domain** | 1 — Agentic Architecture & Orchestration |
| **Difficulty** | 7 / 10 |
| **Estimated effort** | 2:30 |
| **Prerequisites** | L03 — Agentic Loop · L09 — Errors & Tool Distribution |

## Objective

Build the primitives of a **hub-and-spoke** multi-agent research system: a single
**coordinator** that decomposes a query, decides *which* subagents to invoke,
spawns them **in parallel** via the `Task` tool, and passes each one a
**self-contained prompt** — because subagents run with **isolated context** and
never inherit the coordinator's conversation history.

You will implement `orchestrator.py` and prove, with deterministic tests, that:

- a coordinator can only delegate when `"Task"` is in its `allowed_tools`;
- subagent prompts contain the **complete** prior findings (not a summary
  reference), so nothing depends on context inheritance;
- selection is **dynamic** — a simple query uses a small subset, a complex query
  pulls in more specialists, and neither always runs the full pipeline;
- parallel subagents are spawned by emitting **multiple `Task` calls in one
  response**;
- scope partitioning **covers the breadth** of a broad topic (the failure mode
  from Sample Question 7).

## Background

### Hub-and-spoke Architecture

All inter-subagent communication, error handling, and information routing flow
through the coordinator. Subagents never talk to each other directly.

```
                        ┌──────────────────────────────┐
                        │        COORDINATOR           │
                        │  (allowed_tools ⊇ {"Task"})   │
      user query ─────► │  decompose · select · spawn   │
                        │  aggregate · refine           │
                        └───┬────────┬────────┬─────────┘
                            │        │        │      ← parallel Task calls
                            │        │        │        (one response, N blocks)
                 ┌──────────▼─┐  ┌───▼──────┐ ┌▼───────────┐
                 │ web_search │  │doc_analys│ │ synthesis  │   ← ISOLATED context:
                 │ (isolated) │  │(isolated)│ │ (isolated) │     each sees ONLY the
                 └──────────┬─┘  └───┬──────┘ └┬───────────┘     prompt it was given
                            │        │         │
                            └────────┴─────────┘
                                     ▲
                            findings routed back
                            through the coordinator
```

### Isolated Context — No Inheritance (1.3)

A subagent does **not** automatically receive the coordinator's history or the
outputs of sibling subagents. Whatever it needs must be **written into its
prompt**. That is why `build_subagent_prompt` embeds the *complete* prior
findings verbatim (content **and** metadata — source URLs, dates, page numbers)
rather than a reference to "the findings above."

### Dynamic Selection, Not a Fixed Pipeline (1.2)

The coordinator analyses the query and invokes only the relevant subagents. A
one-line factual query does not need document analysis, synthesis, *and* report
writing. Always routing through the full pipeline wastes tokens and latency.

### Parallel Spawning (1.3)

To run subagents concurrently, the coordinator emits **several `Task` tool_use
blocks in a single response**. Emitting one Task per turn serializes them.

### Partition Scope to Cover the Topic (1.2, Sample Question 7)

When decomposing a broad topic, partition it into **distinct, non-overlapping
subtopics that span its breadth**. The classic failure: decomposing "creative
industries" into "digital art," "graphic design," and "photography" — three
flavours of *visual* arts — so music, writing, and film are never researched at
all. The subagents each "succeed," but the report is silently incomplete.

## Tasks

Edit `starter/orchestrator.py`. Keep the public API identical to the solution.

1. **`AgentDefinition`** — dataclass with `name`, `description`, `system_prompt`,
   `allowed_tools` (provided; leave as-is).
2. **`coordinator_can_spawn(coordinator) -> bool`** — `True` iff `"Task"` is in
   `allowed_tools`.
3. **`build_subagent_prompt(goal, prior_findings, quality_criteria) -> str`** —
   embed the goal, the **complete** prior findings (dicts rendered key-by-key so
   metadata stays attached to content; strings verbatim), and the quality
   criteria (goals/quality bars, not step-by-step instructions). Make the
   isolation contract explicit in the text.
4. **`select_subagents(query, registry) -> list[str]`** — infer the query's
   needed capabilities, classify each registered agent, and return the matching
   **subset** of names (registry order). Simple query → few; complex → more;
   never blindly the whole registry.
5. **`spawn_parallel(coordinator, tasks) -> list`** — return one `Task` tool_use
   block per task, all intended for a **single** coordinator response. Raise
   `ValueError` if the coordinator can't spawn or `tasks` is empty.
6. **`partition_scope(topic, n) -> list[str]`** — return `n` distinct,
   non-overlapping subtopics that cover the topic's breadth.
7. **`run_coordination(client, query, registry)`** *(optional but tested)* —
   drive one hub-and-spoke pass over an injected client: coordinator emits
   parallel `Task` calls in one turn, then each subagent runs with a **fresh**
   message list (isolated context). The `client` is injected (a `MockAnthropic`
   in tests) — do not construct `anthropic.Anthropic()` internally.

## Deliverables

- `starter/orchestrator.py` with all functions implemented (same public API as
  `solution/orchestrator.py`).
- All tests in `tests/test_lab19.py` passing against your `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-19-multi-agent-orchestration                    # your work (starter/)
LAB_TARGET=solution uv run pytest lab-19-multi-agent-orchestration   # reference (always green)
```

The tests assert: `coordinator_can_spawn` requires `"Task"` in `allowed_tools`;
`build_subagent_prompt` contains the full prior-findings text (not a summary
reference) with metadata preserved; `select_subagents` returns a one-agent subset
for a simple query and a larger — but not full — subset for a complex one;
`spawn_parallel` yields more than one `Task` block for a single turn;
`partition_scope("creative industries", 4)` returns distinct subtopics covering
music, writing, and film (not just visual arts); and `run_coordination` emits
both Task calls in one coordinator turn while each subagent sees only its
injected context.

## Stretch Goals

- **Iterative refinement loop (1.2).** After synthesis, have the coordinator
  detect coverage gaps (e.g. a partition with no findings) and re-delegate
  targeted `Task` calls to fill them, re-invoking synthesis until coverage is
  sufficient.
- **Scoped `verify_fact` tool (1.3, Sample Question 9).** Give the synthesis
  subagent a narrow `verify_fact` tool for the 85% simple-lookup case, while
  routing the 15% deep verifications back through the coordinator. Add a test
  asserting simple checks never spawn a new subagent.
- **Structured error propagation (1.2 / 5.3).** When a subagent "times out,"
  return structured error context (failure type, attempted query, partial
  results) to the coordinator and have it proceed with an annotated coverage gap
  instead of failing the whole run.
- **Provenance preservation.** Extend `build_subagent_prompt` findings with
  `claim`/`excerpt`/`source`/`date` and assert the synthesis output preserves the
  claim-to-source mapping.
