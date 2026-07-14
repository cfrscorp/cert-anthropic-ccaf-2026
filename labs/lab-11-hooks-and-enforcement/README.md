# L11 — Agent SDK Hooks & Workflow Enforcement

| | |
|---|---|
| **Task statements** | 1.5 — Apply Agent SDK hooks for tool call interception and data normalization; 1.4 — Implement multi-step workflows with enforcement and handoff patterns |
| **Domain** | 1 — Agentic Architecture & Orchestration |
| **Difficulty** | 6 / 10 |
| **Estimated effort** | 2:00 |
| **Prerequisites** | L03 — Agentic Loop Fundamentals; L09 |

## Objective

Build the **programmatic-enforcement layer** that wraps a customer-support agent's
tool calls so critical business rules hold *deterministically*, not just when the
model happens to comply. You will implement four primitives in `hooks.py`:

1. `post_tool_use_normalize` — a **PostToolUse** hook that rewrites heterogeneous
   tool results (Unix ints, ISO-8601 strings, numeric status codes) into one
   canonical shape before the model sees them.
2. `intercept_tool_call` — an **interception** hook that blocks a policy-violating
   action (a refund over $500) and redirects it to human escalation.
3. `PrerequisiteGate` — an ordering gate that blocks `process_refund` until
   `get_customer` has returned a **verified** `customer_id`.
4. `build_handoff` — a **structured handoff** summary for a human who has no
   access to the conversation transcript.

The through-line, and the exam's core point: for rules with financial or
identity consequences, **code-level hooks give guarantees that prompt
instructions cannot** (Sample Question 1).

## Background

### Two Hook Shapes: PostToolUse vs. Interception

The Agent SDK lets you attach hooks at different points in the tool lifecycle.
Two matter here, and they point in opposite directions:

- **`PostToolUse` (result transformation).** Fires *after* a tool runs, *before*
  the model reads the result. Use it to reshape data. Real MCP tools disagree on
  formats — one returns `1719921600` (a Unix epoch), another
  `"2024-07-02T12:00:00Z"` (ISO-8601), another `200`/`503` (numeric status
  codes). Handing that mix to the model burns tokens and invites
  misinterpretation. A `PostToolUse` hook normalizes every result into one
  canonical shape (ISO datetime + status label) so the agent reasons over
  uniform data.

- **Tool-call interception (pre-execution gate).** Fires *before* a tool runs and
  can **block** it. Use it to enforce policy — e.g. refuse a `process_refund`
  above a dollar ceiling and redirect to `escalate_to_human`. The tool never
  executes, so the unsafe action is impossible, not merely discouraged.

```
   model wants to call a tool
             │
             ▼
   ┌───────────────────┐   block  ┌──────────────────────┐
   │ intercept_tool_call│ ───────► │ redirect: escalate   │
   └───────────────────┘          └──────────────────────┘
             │ allow
             ▼
        tool executes
             │
             ▼
   ┌───────────────────┐
   │ post_tool_use_...  │  normalize result → canonical shape
   └───────────────────┘
             │
             ▼
     model sees clean result
```

### Deterministic Enforcement vs. Probabilistic Prompt Compliance

You can *ask* a model to verify identity before refunding, or to never refund
over $500. But a prompt instruction has a **non-zero failure rate**: production
data in the exam scenario shows the agent skipping `get_customer` in 12% of
cases. Few-shot examples lower that rate; they do not zero it. When a mistake
means refunding the wrong account or exceeding a policy ceiling, "usually
complies" is not good enough.

Hooks and prerequisite gates run in **code**. They hold on every call regardless
of the prompt, the phrasing of the request, or model temperature. That is the
distinction the exam draws (Task Statements 1.4 and 1.5, and Sample Question 1):
choose programmatic enforcement when a rule requires *guaranteed* compliance.

### Prerequisite Gates and Structured Handoffs (1.4)

A **prerequisite gate** encodes ordering: a downstream tool cannot run until an
upstream step has produced a required, verified output. Here, `process_refund`
(and `lookup_order`) stay blocked until `get_customer` returns a verified
`customer_id`. When an action *is* blocked — e.g. an over-limit refund — the
agent escalates, and the human needs a **structured handoff**: customer id, root
cause, refund amount, and recommended action, because they cannot see the chat.

## Tasks

Edit **`starter/hooks.py`**. Keep the public API identical to the stubs.

1. **`post_tool_use_normalize(tool_name, result) -> dict`**
   Return a new dict (never mutate `result`) that adds `source_tool`, converts a
   `timestamp` (Unix int/float *or* ISO string, `Z`/naive treated as UTC) to an
   ISO-8601 UTC string, and maps a `status` (numeric HTTP-style code or string)
   to a label: 2xx→`"success"`, 3xx→`"redirect"`, 4xx→`"client_error"`,
   5xx→`"server_error"`; strings are lowercased. Absent fields stay absent.

2. **`intercept_tool_call(tool_name, tool_input, *, refund_limit=500) -> dict`**
   For `process_refund` with an amount (from `"amount"`, else `"refund_amount"`)
   strictly greater than `refund_limit`, return
   `{"action": "block", "redirect": "escalate_to_human", "reason": ...}`.
   Otherwise return `{"action": "allow"}`.

3. **`PrerequisiteGate`**
   `record_tool_result(name, result)` remembers the `customer_id` only when
   `name` is the prerequisite tool and the result has a truthy `customer_id` and
   `verified is True`. `check(tool_name)` returns `False` for a protected tool
   until a verified id exists, `True` otherwise.

4. **`build_handoff(context) -> dict`**
   Return `customer_id`, `root_cause`, `refund_amount`, `recommended_action`
   (defaulting to `None`), plus `escalated_to: "human"`.

## Deliverables

- A completed `starter/hooks.py` that passes the test suite.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-11-hooks-and-enforcement
```

All 15 tests should pass. To confirm your work matches the reference behavior,
you can also run the solution:

```bash
LAB_TARGET=solution uv run pytest lab-11-hooks-and-enforcement
```

## Stretch Goals

- **Wire the hooks into an agentic loop.** Reuse your L03 `run_agent` and call
  `intercept_tool_call` before each tool executes and `post_tool_use_normalize`
  on each result. When a call is blocked, feed the redirect back as the tool
  result so the model escalates instead of retrying.
- **Generalize the gate.** Support arbitrary prerequisite→dependent tool maps
  (e.g. `verify_payment_method` before `charge_card`) instead of a single
  hard-coded pair.
- **Normalize more shapes.** Add currency normalization (cents vs. dollars,
  `"$6.00"` strings) so downstream refund logic compares apples to apples.
- **Contrast with a prompt-only baseline.** Write a short note explaining why a
  system-prompt rule ("never refund over $500") cannot give the same guarantee
  as `intercept_tool_call`, tying back to Sample Question 1.
