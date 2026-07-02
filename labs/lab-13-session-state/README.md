# L13 — Session State, Resumption & Forking

| | |
|---|---|
| **Task statement** | 1.7 — Manage session state, resumption, and forking |
| **Domain** | 1 — Agentic Architecture & Orchestration |
| **Difficulty** | 5 / 10 |
| **Estimated effort** | 1:30 |
| **Prerequisites** | L03 — Agentic Loop Fundamentals |

## Objective

Model the mechanics of **named sessions** so you can reason about the three
decisions Task Statement 1.7 tests: how to **resume** a prior conversation, how
to **fork** a shared baseline into independent branches, and when to **abandon a
resume in favor of a fresh session seeded with a structured summary**. You will
implement a small, offline `SessionStore` plus two helper functions, and prove
their semantics with deterministic tests.

You are not calling a live agent here. The point is the *state model* around the
agent — the part your code owns.

## Background

When you run an agent over several work sessions, the conversation (messages plus
the tool results the agent gathered) is the state you carry forward. The SDK/CLI
give you three levers over that state.

### `--resume <session-name>`

A named session persists the full conversation to disk. Later you continue it
with `--resume <session-name>`: the agent picks up with its entire prior context
— everything it read, ran, and concluded. Resuming is **cheap** and preserves
hard-won context, so it is the default when that context is still valid.

In this lab, `SessionStore.save(name, messages)` persists a named conversation
and `SessionStore.resume(name)` returns the prior history so you can append new
turns and continue.

### `fork_session` — independent branches from a shared baseline

Sometimes you have done expensive shared analysis (the agent has read and mapped
a codebase) and now want to explore **two divergent approaches** from that same
starting point — say, a mock-based test strategy vs. an integration-test
strategy, or two refactors. `fork_session` branches the baseline into an
**independent** copy. Work done in one branch must **not** leak into the other or
back into the baseline.

The load-bearing property is independence: in this lab `fork(name, new_name)`
**deep-copies** the baseline. Appending to (or mutating anything inside) the fork
leaves the original untouched. A shallow copy would share nested message
objects and silently corrupt the baseline — that is the classic bug this lab
guards against.

### Resume vs. restart-with-summary (stale vs. fresh)

Resuming replays **all** prior tool results as if they were still true. That is
great when they are — but if the code has changed since, those results are
**stale**, and the agent will confidently reason over a snapshot of the world
that no longer exists. When prior tool results are stale, it is **more reliable
to start a NEW session seeded with a structured summary** (your own concise,
current statement of where things stand) than to resume on top of stale results.

- Prior context still valid → **resume** (keep the full conversation).
- Prior tool results stale → **restart with a structured summary** (fresh
  session, no misleading history).

`should_resume(prior_results_stale)` encodes exactly this decision.

### Informing a resumed session about file changes

When you *do* resume after modifying files the agent already analyzed, do not
silently let it trust its stale reading, and do not force a wasteful full
re-exploration. Instead **tell it exactly which files changed** so it does
*targeted* re-analysis of just those files.
`inject_file_change_notice(messages, changed_files)` appends a user turn naming
the changed files.

## Tasks

Edit `starter/sessions.py` and implement the public API (it must match
`solution/sessions.py`):

1. **`SessionStore(path=None)`** — in-memory by default; if `path` is given, back
   the store with a JSON file (load existing state on construction, flush on
   every mutation) so a session saved by one instance can be resumed by another.
2. **`save(name, messages)`** — store a **deep copy** of `messages` under `name`.
3. **`resume(name) -> list`** — return a **deep copy** of the prior history;
   raise `KeyError` for an unknown name.
4. **`fork(name, new_name) -> str`** — create an **independent deep-copied**
   branch and return `new_name`. Mutating the fork must never touch the original.
5. **`list_sessions() -> list`** — the known names, sorted.
6. **`should_resume(prior_results_stale) -> str`** — `"restart_with_summary"`
   when stale, `"resume"` when fresh.
7. **`inject_file_change_notice(messages, changed_files) -> list`** — return a
   **new** list (do not mutate the input); when `changed_files` is non-empty,
   append a `{"role": "user", ...}` turn whose content names each changed file.
   An empty list is a no-op.

## Deliverables

- `starter/sessions.py` implemented to match the public API in
  `solution/sessions.py`.
- All tests in `tests/test_lab13.py` passing against your `starter/`.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-13-session-state                     # your work (starter/) — should pass when done
LAB_TARGET=solution uv run pytest lab-13-session-state # the reference solution — always green
```

The tests assert: `save` + `resume` round-trips history; a JSON-backed session
survives across store instances; a **fork is independent** (appending to the fork
leaves the baseline unchanged, including nested content); `should_resume` returns
`"restart_with_summary"` when stale and `"resume"` when fresh; and
`inject_file_change_notice` appends a notice that references every changed file
(and is a no-op for an empty list).

## Stretch goals

- **Summary-seeded restart.** Add `restart_with_summary(name, summary) -> list`
  that starts a fresh session whose first turn is your structured summary,
  *without* dragging in the stale history — the concrete counterpart to the
  `should_resume` decision.
- **Fork lineage.** Record each fork's parent so `list_sessions()` can show a
  simple tree (`baseline → approach_a`, `baseline → approach_b`).
- **Divergence diff.** Add a helper that, given two forked sessions, returns the
  turns each has that the other does not — a quick way to compare two approaches.
- **Staleness by fingerprint.** Instead of a boolean, store a content hash of
  each analyzed file at save time; compute `prior_results_stale` by re-hashing at
  resume time so the resume/restart decision is derived, not asserted.
