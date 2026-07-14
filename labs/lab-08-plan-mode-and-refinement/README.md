# L08 — Plan Mode, Direct Execution & Iterative Refinement

| | |
|---|---|
| **Task statements** | 3.4 — Determine when to use plan mode vs direct execution · 3.5 — Apply iterative refinement techniques for progressive improvement |
| **Domain** | 3 — Claude Code Configuration & Workflows |
| **Difficulty** | 3 / 10 |
| **Estimated effort** | 1:30 |
| **Prerequisites** | L02 — Claude Code Config Foundations |

## Objective

Turn two of the exam's judgment calls into code you can reason about and test:

1. **Plan mode vs direct execution** — given a task, decide whether to explore and
   design first (plan) or just make the change (direct), and whether the discovery
   phase should be delegated to the **Explore subagent**.
2. **Iterative refinement** — given a set of issues to fix, decide whether to send
   them in a **single message** (because the fixes interact) or iterate on them
   **sequentially** (because they are independent).

You will implement three pure functions in `starter/decisions.py` and prove, with
deterministic tests, that they match the canonical cases in `scenarios.md` —
including the Sample-Question-5 monolith→microservices restructuring and the
single-file bug-fix.

## Background

### Plan Mode vs Direct Execution (Task Statement 3.4)

**Plan mode** lets Claude explore a codebase and design an approach *before*
committing to changes. It is built for complex work:

- **large-scale / multi-file changes** (e.g. a library migration touching 45+ files),
- **architectural decisions** (service boundaries, module dependencies),
- **multiple valid approaches** (e.g. choosing between two integration designs with
  different infrastructure), and
- anything whose **scope is not yet clear** and needs investigation first.

Planning up front prevents the costly rework that happens when a dependency or a
better design is discovered halfway through implementation.

**Direct execution** is the right call for **simple, well-scoped** changes where you
already understand what to do: a single-file bug fix with a clear stack trace,
adding one date-validation conditional, dropping in a null guard. Reaching for plan
mode here just adds ceremony.

A key exam trap (Sample Question 5): when the complexity is **already stated in the
requirements**, you enter plan mode *up front*. "Start direct and switch to plan
mode later if it gets complicated" and "use direct execution with comprehensive
upfront instructions" are both wrong — the first ignores stated complexity, the
second assumes you already know the right structure without exploring.

You can also **combine** the two: use plan mode to *investigate* and design a
migration, then use direct execution to *implement* each already-planned step.

### The Explore Subagent

Discovery is noisy: reading many files, tracing call flows, and grepping produces a
lot of output whose raw form has little lasting value but eats your context window.
The **Explore subagent** isolates that verbose, multi-phase discovery in its own
context and returns a concise summary, keeping the main conversation focused. Use it
when discovery is **verbose AND** would otherwise burden the main session (it is part
of a multi-phase task, or risks exhausting context). Don't spawn it for a quick,
self-contained lookup — the overhead isn't worth it.

### Iterative Refinement Patterns (Task Statement 3.5)

Several techniques make Claude converge faster on what you actually want:

- **Concrete input/output examples** — 2-3 example transformations communicate a
  requirement far more reliably than prose, which gets interpreted inconsistently.
- **Test-driven iteration** — write the test suite first (expected behavior, edge
  cases, performance), then iterate by *sharing the failures* as feedback.
- **The interview pattern** — have Claude ask you questions first, surfacing
  considerations (cache invalidation, failure modes) you hadn't specified — useful
  in unfamiliar domains before any code is written.
- **Single message vs sequential** — this is the decision you'll encode. When the
  fixes **interact** (changing one reshapes another), describe them all in **one
  detailed message** so the model reconciles the coupling in a single pass. When the
  issues are **independent**, iterate **sequentially** — one fix at a time — so each
  change stays small and easy to review.

## Tasks

Edit `starter/decisions.py` and implement three pure functions (same public API as
`solution/decisions.py`). The exact decision rules are in each function's docstring
and in `scenarios.md`.

1. **`choose_mode(task: dict) -> str`** → `"plan"` or `"direct"`.
   Return `"plan"` if the task is architectural, has multiple valid approaches, is
   multi-file (`multi_file_count > 1`), or has unclear scope; otherwise `"direct"`.

2. **`refinement_strategy(issues: list[dict]) -> str`** → `"single_message"` or
   `"sequential"`. Return `"single_message"` if any issue has
   `interacts_with_others` truthy; otherwise `"sequential"` (an empty list is
   `"sequential"`).

3. **`should_use_explore(task: dict) -> bool`** → `True` when
   `verbose_discovery` is set **and** (`multi_phase` or `context_exhaustion_risk`);
   otherwise `False`.

Keep the functions pure — no I/O, no globals. The tests parametrize over the
canonical scenarios and assert exact labels.

## Deliverables

- `starter/decisions.py` with working `choose_mode`, `refinement_strategy`, and
  `should_use_explore` (matching the public API in `solution/decisions.py`).
- All tests in `tests/test_lab08.py` passing against your `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-08-plan-mode-and-refinement            # your work (starter/) — should pass when done
LAB_TARGET=solution uv run pytest lab-08-plan-mode-and-refinement   # reference solution — always green
```

The suite parametrizes over every row in `scenarios.md` for all three functions,
and adds explicit checks for the monolith-restructuring (→ plan) and single-file
bug-fix (→ direct) cases, plus boundary cases (multi-file-alone → plan, unclear
scope → plan, verbose-discovery-without-burden → no Explore).

## Stretch Goals

- **Confidence/reasoning output.** Extend `choose_mode` to return a
  `(mode, reasons)` tuple listing which triggers fired, without breaking the
  string-returning tests (add a `explain=` keyword).
- **Weighted scoring.** Replace the boolean OR in `choose_mode` with a score over
  weighted features and a threshold; show it still reproduces every canonical row.
- **New scenarios.** Add two rows to `scenarios.md` (one plan, one direct) that
  probe the boundary — e.g. a mechanical multi-file rename — and mirror them in the
  test tables. Decide and justify the label.
- **Refinement richness.** Model *dependency chains* between issues (issue B depends
  on A) and decide whether the single-message rule still holds or needs ordering.
