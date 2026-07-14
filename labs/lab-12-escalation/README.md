# L12 — Escalation & Ambiguity Resolution

| | |
|---|---|
| **Task statement** | 5.2 — Design effective escalation and ambiguity resolution patterns |
| **Domain** | 5 — Escalation, Reliability & Self-Evaluation |
| **Difficulty** | 5 / 10 |
| **Estimated effort** | 1:30 |
| **Prerequisites** | L03 — Agentic Loop Fundamentals · L06 — Error Handling |

## Objective

Build the decision core of a support agent that knows **when to escalate to a
human, when to ask a clarifying question, and when to resolve autonomously** —
and, just as importantly, knows what signals to *ignore*. You will implement
three pure functions and prove with deterministic tests that the decision is
driven by **explicit, structural triggers**, not by customer sentiment or the
agent's own self-reported confidence.

## Background

An agent aiming for high first-contact resolution has to be *calibrated*: it must
handle routine cases itself but hand off the ones a human should own. The exam
guide (Task Statement 5.2) names the triggers that should drive an escalation:

- **Explicit customer request for a human** — honor it *immediately*, without
  first attempting an investigation.
- **Policy exceptions / gaps** — escalate when the written policy is *silent,
  ambiguous, or has a gap* on the customer's specific request. The canonical
  example: the customer wants a competitor price-match, but policy only addresses
  your own-site price adjustments. That is a policy gap, not merely a "complex"
  case.
- **Inability to make meaningful progress** — e.g. the backend the agent needs is
  down.

And the trigger for a *clarifying question* rather than a guess:

- **Multiple customer matches** — when a lookup returns more than one record, ask
  for an additional identifier. Do **not** pick one by a heuristic
  ("most recent order", "closest name").

The subtle, heavily tested point is what **not** to use:

> **Sentiment and self-reported confidence are unreliable proxies for case
> complexity.** A furious customer with a routine refund should still be helped;
> a cheerful request that needs a policy exception should still escalate. And an
> agent's "I'm 95% sure" is *least* trustworthy on exactly the hard cases it
> gets wrong.

This is the situation in **Sample Question 3**: an agent escalates easy cases
(standard damage replacements with photos) while trying to autonomously handle
ones that need policy exceptions, sinking first-contact resolution to 55%. The
correct fix (answer **A**) is to add **explicit escalation criteria with few-shot
examples** to the system prompt. Deploying sentiment analysis (D) solves a
different problem — sentiment does not correlate with complexity. Trusting a
model-reported confidence threshold (B) fails because that confidence is poorly
calibrated. A trained classifier (C) is over-engineering before prompt
optimization has even been tried.

You will encode all of this as testable logic, and then produce the very prompt
artifact answer A calls for.

## The Decision & the Context Schema

`decide(context)` returns exactly one of `"ESCALATE"`, `"ASK_CLARIFY"`,
`"RESOLVE"`. The `context` dict uses these keys (all optional, with safe
defaults):

| Key | Type | Default | Meaning |
|---|---|---|---|
| `explicit_human_request` | bool | `False` | Customer directly asked for a human this turn. |
| `reiterated_human_request` | bool | `False` | Customer repeated the ask after being offered a resolution. |
| `customer_matches` | int | `1` | How many records match the supplied identifiers. |
| `policy_status` | str | `"covered"` | One of `covered` / `gap` / `silent` / `ambiguous`. |
| `can_make_progress` | bool | `True` | Tools reachable / data available. |
| `within_capability` | bool | `True` | Action is permitted/possible for the agent. |
| `straightforward` | bool | `True` | Routine given everything above. |
| `sentiment` | str | — | **Ignored.** Present only to prove it is not used. |
| `self_reported_confidence` | float | — | **Ignored.** Same. |

Apply the checks in this **priority order**:

1. Explicit **or** reiterated human request → `ESCALATE` (immediately, before any
   investigation).
2. `customer_matches > 1` → `ASK_CLARIFY` (request another identifier).
3. `policy_status` in `{gap, silent, ambiguous}` → `ESCALATE`.
4. `can_make_progress` is `False` → `ESCALATE`.
5. `within_capability` is `False` → `ESCALATE`.
6. `straightforward` and within capability → `RESOLVE`.
7. Anything left → `ESCALATE` (safe default).

## Tasks

Edit `starter/escalation.py` and implement three functions (public API matches
`solution/escalation.py`):

1. **`decide(context: dict) -> str`** — the priority-ordered logic above. It must
   **never** read `context["sentiment"]` or `context["self_reported_confidence"]`.

2. **`uses_unreliable_signal(policy: dict) -> bool`** — a lint over a *policy*
   specification (e.g. `{"name": ..., "signals": [...]}`). Recursively inspect
   the policy's keys and string values and return `True` if any references an
   unreliable signal (substrings like `sentiment`, `confidence`, `frustration`,
   `mood`, `tone`).

3. **`build_escalation_criteria(examples: list[dict]) -> str`** — return a
   system-prompt snippet that states the explicit criteria **and** embeds every
   few-shot example (`situation` / `decision` / optional `reason`) verbatim. This
   is the concrete artifact from Sample Question 3, answer A. Raise `ValueError`
   on empty `examples`.

The scenarios in `cases.json` (10 labeled cases) are what the tests iterate over,
including: a customer demanding a human (`ESCALATE`), a competitor price-match
that policy is silent on (`ESCALATE`), two customers named "J. Smith"
(`ASK_CLARIFY`), a standard damaged-item replacement with a photo (`RESOLVE`),
and a frustrated-but-resolvable case (`RESOLVE` unless the human request is
reiterated).

## Deliverables

- `starter/escalation.py` with all three functions implemented.
- All tests in `tests/test_lab12.py` passing against your `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-12-escalation                       # your work (starter/)
LAB_TARGET=solution uv run pytest lab-12-escalation   # reference — always green
```

The suite checks that `decide()` matches every labeled case; that flipping
`sentiment` across the spectrum and sweeping `self_reported_confidence` from 0.0
to 1.0 **never** change a decision; that `uses_unreliable_signal` flags a
sentiment/confidence policy and clears a criteria-based one; and that
`build_escalation_criteria` embeds the examples it is given.

## Stretch Goals

- **Structured handoff.** Extend `decide` to also return a reason code and, when
  escalating, a short handoff summary (customer id, root cause, recommended
  action) — the structured handoff pattern from Task Statement 5.2 that a human
  agent (who lacks the transcript) needs.
- **Wire it into an agent loop.** Reuse your L03 `run_agent` with an
  `escalate_to_human` tool and a `tool_choice` nudge, and use `decide` inside the
  tool executor so escalation is driven by these criteria rather than the model's
  mood-reading.
- **Confidence, done right (5.5).** Instead of the model's self-reported number,
  route on a *structural* uncertainty signal (e.g. contradictory tool results)
  and compare how much better-calibrated it is on the `policy_status == "gap"`
  cases.
- **LLM-graded prompt.** Feed `build_escalation_criteria(...)` output to a live
  Claude call over a held-out scenario and `grade` (mark it `@pytest.mark.llm`)
  whether the model picks the labeled action.
