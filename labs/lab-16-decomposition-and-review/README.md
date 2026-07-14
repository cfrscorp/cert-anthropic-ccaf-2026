# Lab 16 — Task Decomposition & Multi-pass Review

| | |
|---|---|
| **Domain** | 1 — Agentic Architecture & Orchestration · 4 — Prompt Engineering & Structured Output |
| **Task statements** | 1.6 — Design task decomposition strategies · 4.6 — Design multi-instance and multi-pass review architectures |
| **Difficulty** | 6 / 10 |
| **Estimated time** | 2:00 |
| **Prerequisites** | L06 |

`1.6, 4.6 · Difficulty 6/10 · Est 2:00 · Prerequisites: L06`

## Objective

Learn to pick the right **task decomposition** for a workflow and to structure a
**multi-pass, multi-instance review** that stays consistent at scale. You will
implement the decision logic that:

1. Chooses **prompt chaining** (a fixed sequential pipeline) for predictable,
   multi-aspect work versus **dynamic** decomposition for open-ended
   investigation whose subtasks emerge from intermediate findings (**1.6**).
2. Plans a review as **one local pass per file plus exactly one cross-file
   integration pass** to avoid attention dilution (**1.6 / 4.6**).
3. Distinguishes an **independent review instance** from a **self-review** that
   still carries the generator's reasoning context (**4.6**).
4. Routes findings by **self-reported confidence** to auto-apply versus human
   review (**4.6**).

## Background

Two failure modes motivate this lab.

**Wrong decomposition (1.6).** Some tasks have a knowable set of subtasks up
front — "review each of these files, then run an integration pass." Those want a
**fixed sequential pipeline (prompt chaining)**: predictable, cheaper, easy to
reason about. Other tasks are genuinely open-ended — "add comprehensive tests to
a legacy codebase" — where you cannot enumerate subtasks in advance. You must map
structure, find high-impact areas, and generate a plan that **adapts as
dependencies are discovered**. That wants **dynamic** decomposition. Choosing a
fixed pipeline for an open-ended task under-covers it; choosing dynamic
decomposition for a predictable task adds needless overhead.

**Diluted, self-referential review (4.6).** This is Sample Question 12: a pull
request modifies **14 files**, and a single review pass over all of them gives
inconsistent depth, misses obvious bugs, and even contradicts itself — flagging a
pattern in one file while approving identical code in another. The root cause is
**attention dilution**, not model size. The fix is to split into **per-file local
passes plus one cross-file integration pass**. Two related ideas compound the
benefit: an **independent** review instance (one that never saw the generation
reasoning) catches subtle issues a **self-review** will not, and having each
finding **self-report confidence** lets you route review attention where it is
needed. See `review_scenario.md` for the full canonical case.

Why the seductive alternatives lose (Sample Q12): a **bigger model / larger
context** does not fix attention *quality*; forcing **smaller PRs** shifts burden
to developers without improving the system; **consensus of 3 full-PR runs**
suppresses the intermittently-caught real bugs you most want to keep.

## Tasks

Work in `starter/decomposition.py`. Each function raises `NotImplementedError`
until you implement it; keep the same public API as `solution/`.

1. **`choose_decomposition(task: dict) -> str`** — return `"prompt_chaining"` for
   predictable multi-aspect work and `"dynamic"` for open-ended investigation.
   Honour an explicit `open_ended` flag, a known `type`, and keyword signals in
   the task's `goal`/`description`.

2. **`plan_review_passes(files: list[str]) -> list[dict]`** — return exactly one
   `local` pass per file plus **exactly one** `integration` pass (last, spanning
   all files). For N files, N + 1 entries.

3. **`is_independent_review(review_context: dict) -> bool`** — return `False` when
   the reviewer shares the generator's reasoning context (self-review) and `True`
   for a fresh instance.

4. **`route_by_confidence(findings: list[dict], threshold: float) -> dict`** —
   partition findings into `"auto"` (confidence at/above threshold) and
   `"human_review"` (below, or missing confidence).

5. **`independent_second_pass(client, review_target, *, model=...)`** *(optional,
   already exercised by a mock test)* — drive an injected `client` to run a fresh
   review that emits structured `report_finding` tool calls, and return the
   parsed findings.

## Deliverables

- `starter/decomposition.py` with the functions implemented.
- (Reference) `solution/decomposition.py` — the complete implementation.
- `review_scenario.md` — the canonical 14-file PR case (provided).

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-16-decomposition-and-review
```

All tests should pass once you finish `starter/`. To validate the reference
solution the same way the program's grader does:

```bash
LAB_TARGET=solution uv run pytest lab-16-decomposition-and-review -q
```

## Stretch Goals

- **Adaptive plan for the legacy-tests task.** Sketch the dynamic decomposition
  for "add comprehensive tests to a legacy codebase": map structure → identify
  high-impact / high-risk modules → produce a prioritized plan that re-plans as
  dependencies surface. Contrast it with the fixed 15-pass review plan.
- **Confidence calibration (5.5).** `route_by_confidence` trusts self-reported
  confidence. Describe how you would calibrate the threshold against a labeled
  validation set, and why raw LLM confidence is an unreliable proxy on its own.
- **Second-instance disagreement.** Extend `independent_second_pass` (or the mock
  test) so the independent reviewer *disagrees* with a generator finding, and
  decide how the disagreement should be surfaced for human review.
