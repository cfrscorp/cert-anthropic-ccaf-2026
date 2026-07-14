# L22 — Capstone: Customer Support Resolution Agent

| | |
|---|---|
| **Scenario / Exercise** | S1 — Customer Support Resolution Agent / Preparation Exercise 1 |
| **Primary domains** | 1 — Agentic Architecture & Orchestration; 2 — Tool Design & MCP Integration; 5 — Context Management & Reliability |
| **Task statements** | 1.1, 1.4, 1.5, 2.1, 2.2, 5.1, 5.2 |
| **Difficulty** | 8 / 10 |
| **Estimated effort** | 3:00 |
| **Prerequisites** | L11 — Hooks & Enforcement; L12 — Escalation; L14 — Context Management |

## Objective

Integrate the pieces you built in earlier labs into **one** production-shaped
customer-support agent. The agent runs a model-driven agentic loop over four
MCP-style tools and wraps that loop in the deterministic guarantees the exam's
Scenario 1 demands. Your target is the scenario's own: **80%+ first-contact
resolution while knowing when to escalate.**

You will assemble three modules with a fixed public API:

- `tools.py` — the four tools (`get_customer`, `lookup_order`, `process_refund`,
  `escalate_to_human`) with **disambiguating descriptions** and **structured
  error responses**.
- `guardrails.py` — a `PrerequisiteGate`, a refund **interception hook**,
  `build_handoff`, and an explicit-human-request detector.
- `support_agent.py` — `run_support_agent(...)` that drives the loop, extracts a
  persistent **case-facts** block, decomposes **multi-concern** messages, and
  makes the escalation/clarification decisions.

This is a capstone: it is **self-contained** (no imports from other labs) and it
reimplements the pieces it needs so the whole system lives in one folder.

## Background

Scenario 1 gives you tools into backend systems and a blunt reliability bar. The
sample questions expose the traps:

- **Skipping identity verification (SQ1).** In 12% of cases a prompted agent
  calls `lookup_order`/`process_refund` before `get_customer`, refunding the
  wrong account. The fix is a **programmatic prerequisite gate**, not a stronger
  prompt — prompt compliance is probabilistic (Task Statements 1.4/1.5).
- **Over-limit refunds.** A refund above $500 must never execute autonomously. A
  **tool-call interception hook** blocks it deterministically and redirects to
  human escalation (Task Statement 1.5).
- **Ambiguous tool selection (SQ2).** `get_customer` and `lookup_order` take
  similar identifiers; only **detailed, differentiated descriptions** route
  reliably (Task Statement 2.1).
- **Miscalibrated escalation (SQ3).** The agent must escalate on **explicit
  requests, policy gaps, and inability to progress** — not on sentiment or
  self-reported confidence. Multiple customer matches call for a **clarifying
  question**, not a heuristic guess (Task Statement 5.2).
- **Losing the numbers (5.1).** Progressive summarization blurs amounts, dates,
  order numbers, and statuses. A **persistent case-facts block**, re-injected
  each turn outside the summarized history, keeps them verbatim.
- **Structured errors (2.2).** A transient failure should be **retried**; a
  business failure should be **explained**. Uniform "operation failed" strings
  prevent that decision.

The loop itself terminates **only on `stop_reason`** (`tool_use` continues,
`end_turn` ends). Never parse assistant prose or use an iteration count as the
primary stop (Task Statement 1.1).

## Tasks

Edit the three modules in **`starter/`**. Keep every public name identical to the
stubs so the shared test suite runs unchanged.

1. **Tools with disambiguating descriptions (2.1).** In `tools.py`, write the
   four `TOOLS` schemas so each states its input format, an example query,
   edge-case behaviour, and an explicit "use this when … not when …" boundary
   pointing at its sibling. Add `input_schema` per tool.

2. **Structured errors (2.2 / 5.3).** Implement `make_error(category, message,
   *, retryable=None)` returning `{isError, errorCategory, isRetryable,
   message}` — only `transient` is retryable by default. Implement
   `execute_tool(name, input, backends)` so it: honours per-tool callable
   overrides in `backends`, catches backend exceptions as transient errors, and
   returns a **valid empty result** (`found: False`) for a missing order rather
   than an error.

3. **Prerequisite gate (1.4 / SQ1).** In `guardrails.py`, implement
   `PrerequisiteGate` so `lookup_order`/`process_refund` are blocked until a
   `get_customer` result with a truthy `customer_id` **and** `verified is True`
   unlocks it.

4. **Refund interception + handoff (1.5 / 1.4).** Implement `intercept_tool_call`
   (block `process_refund` strictly above `refund_limit`, redirect to
   `escalate_to_human`) and `build_handoff` (customer_id, root_cause,
   refund_amount, recommended_action → None if missing; plus `escalated_to`).

5. **Explicit human request (5.2).** Implement `wants_human(message)` on an
   explicit phrase list (do not trip on a bare "human").

6. **Case facts + concerns (5.1 / 1.4).** In `support_agent.py`, implement
   `extract_case_facts(sources)` (amounts, dates, order numbers, statuses, from
   the message and every tool result) and `decompose_concerns(message)`.

7. **The agent (1.1 + all of the above).** Implement `run_support_agent` so it:
   - short-circuits to escalation on an explicit human request, **without any
     investigation** (no model call, no tools);
   - otherwise runs the loop, applying interception **then** the gate before
     executing each requested tool;
   - retries a transient tool error locally, but returns a business error for the
     model to explain;
   - flags `clarification_requested` when `get_customer` returns multiple
     matches (and leaves the gate locked);
   - rebuilds the system prompt (with the live case-facts block and escalation
     few-shot) each turn;
   - returns the documented result dict.

## Deliverables

- Completed `starter/tools.py`, `starter/guardrails.py`, and
  `starter/support_agent.py` that pass the full test suite.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-22-capstone-support-agent
```

All tests should pass. To confirm your work matches the reference behaviour:

```bash
LAB_TARGET=solution uv run pytest lab-22-capstone-support-agent
```

`scenarios.json` documents the six labeled end-to-end cases the tests exercise
(misidentification prevented, $600 refund blocked & escalated, explicit human
request, multiple matches → clarify, multi-concern message, standard resolvable
case) with the model plan and expected outcome for each.

## Stretch Goals

- **Trim tool outputs before they land in context (5.1).** `lookup_order`
  already drops internal fields; extend trimming so only refund-relevant fields
  survive, and measure the token savings across a long session.
- **Generalize the gate.** Support arbitrary prerequisite→dependent maps (e.g.
  `verify_payment_method` before `charge_card`) instead of the hard-coded pair.
- **Add a `PostToolUse` normalization hook.** Canonicalize heterogeneous
  timestamps/status codes from the tools before the model reads them (Task
  Statement 1.5) and feed the normalized result into the case-facts block.
- **Reiterated-request handling (5.2).** Acknowledge frustration and offer a
  resolution first; escalate only if the customer repeats the request for a
  human — contrast this with the immediate-escalation path.
- **Policy-gap escalation.** Add a `policy_status` signal so a request the policy
  is silent on (e.g. competitor price matching) escalates as a policy gap.
