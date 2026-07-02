# L22 Solution — Capstone: Customer Support Resolution Agent

## Approach

The capstone is deliberately an *integration* exercise: every piece maps to a
sample-question "correct answer," and the distractors are the shortcuts you must
not take. The system has three layers:

1. **Tools (`tools.py`)** — the data/backend surface. Descriptions do the
   tool-selection work (2.1); results carry structured error metadata (2.2).
2. **Guardrails (`guardrails.py`)** — deterministic, code-level enforcement that
   holds regardless of the prompt (1.4, 1.5, 5.2).
3. **Agent (`support_agent.py`)** — the model-driven loop (1.1) that applies the
   guardrails, maintains the case-facts block (5.1), decomposes multi-concern
   messages (1.4), and makes the escalation/clarification calls (5.2).

The Claude client is injected, so the entire system is exercised offline with a
scripted `MockAnthropic`: the mock decides *what the model wants to do*, and the
guardrails decide *what is actually allowed to happen*. That separation is the
whole point — the guarantees do not depend on the model behaving.

## Key decisions & why (correct answers vs. distractors)

| Decision | Exam grounding | Rejected distractor |
|---|---|---|
| **Prerequisite gate** blocks order ops until `get_customer` verifies identity, in code | SQ1 **A** — programmatic prerequisite | "Strengthen the system prompt" (B) / "add few-shot examples" (C): both only lower a *probabilistic* failure rate; unacceptable for money/identity |
| **Interception hook** blocks refunds > $500 and redirects to escalation | Task 1.5 — hooks for guaranteed compliance | A prompt rule "never refund over $500": non-zero failure rate |
| Apply **interception before the gate** | 1.5 then 1.4 | Running the tool then "undoing" it: the unsafe action already happened |
| **Detailed, differentiated tool descriptions** with input format / example / boundary | SQ2 **B** — descriptions are the primary selection mechanism | Few-shot (A: token overhead, doesn't fix the root cause); routing layer (C: over-engineered); consolidating tools (D: more effort than a "first step") |
| **Explicit human request → escalate immediately, no investigation** | Task 5.2 | Investigating first (ignores the explicit request); escalating on sentiment |
| **Multiple matches → ask for an identifier**; gate stays locked | Task 5.2 | Picking a match by heuristic ("most recent order") |
| Escalation driven by **explicit triggers**, never sentiment/confidence | SQ3 **A** | Confidence threshold (B: LLM confidence is poorly calibrated on hard cases); classifier (C: over-engineered); sentiment (D: uncorrelated with complexity) |
| **Structured errors**: retry transient, explain business | Task 2.2 | Uniform "operation failed"; retrying a non-retryable business error |
| **Empty result ≠ failure** (`found: False` vs. an error object) | Task 5.3 | Marking a valid empty result as an error, or hiding a failure as empty success |
| **Persistent case-facts block** re-injected each turn, outside summarized history | Task 5.1 | Letting progressive summarization blur "$129.99" into "about $130" |
| **Loop terminates only on `stop_reason`** | Task 1.1 | Parsing assistant text for "done"; using an iteration cap as the primary stop (here it is only a backstop) |

## Reference walkthrough

**`tools.py`.** `TOOLS` gives each tool a description with the four elements from
2.1. `get_customer` returns `verified: True` + a `customer_id` on a single match,
`match_count > 1` with candidates on ambiguity (verified false), and
`match_count: 0` on no match. `lookup_order` returns `found: False` for a missing
order (a valid empty result). `process_refund` returns a **business** error for
an ineligible order; the over-limit rule is *not* here — it belongs in the hook.
`execute_tool` honours a callable override in `backends` (how the test injects a
transient-then-success sequence) and wraps any backend exception as a transient
error.

**`guardrails.py`.** `PrerequisiteGate` only unlocks on `verified is True` +
truthy `customer_id`, so a multi-match `get_customer` does **not** unlock it.
`intercept_tool_call` blocks a `process_refund` strictly above the limit and
returns a `redirect`. `build_handoff` surfaces missing keys as `None` (never
dropped) so the human sees what is unknown. `wants_human` matches an explicit
phrase list and normalizes whitespace, so it won't trip on a bare "human."

**`support_agent.py`.** `run_support_agent`:
1. Decomposes concerns and seeds the case-facts block from the message.
2. **Pre-check:** if `wants_human`, build the handoff and return immediately —
   `iterations == 0`, no model call, no tools. (This is what "immediately,
   without investigation" means, and the test asserts `client.calls == []`.)
3. Otherwise loops: build the system prompt (with the live facts block +
   escalation few-shot), call the model, and stop only when `stop_reason !=
   "tool_use"`.
4. For each requested tool: **interception first** (block over-limit refund →
   escalate + handoff), **then the gate** (refuse account ops before
   verification), then execute with local retry for transient errors only.
5. Records `clarification_requested` on a multi-match `get_customer`, refreshes
   the case-facts block from each tool result, and returns the full result dict.

## Common mistakes

- **Enforcing rules in the prompt instead of in code.** The tests block a refund
  even though the scripted "model" tried to make it — because the hook, not the
  prompt, decides. If your enforcement lives only in the system prompt, the
  guardrail tests fail.
- **Unlocking the gate on any `get_customer` result.** A multi-match result must
  leave the gate locked; otherwise the clarification path lets a refund through.
- **Retrying business/validation errors.** Only `transient` is retryable. The
  business-error test asserts `attempts == 1`.
- **Treating a missing order as an error.** `lookup_order` on an unknown id is a
  valid empty result (`found: False`), not an access failure.
- **Terminating on assistant text or an iteration count.** Loop on `stop_reason`
  only; the `safety_cap` is a backstop, not the stop signal.
- **Letting the case-facts block drop tool-sourced values.** The persistence test
  checks that `$129.99` — which appears only in the tool result — survives.
- **Investigating before honouring an explicit human request.** The short-circuit
  must run before the loop, with no tool calls.

## Checklist

- [ ] `TOOLS` descriptions state input format, example, edge cases, and a
      "use this when … not when …" boundary for `get_customer` vs `lookup_order`.
- [ ] `make_error` marks only `transient` retryable; `execute_tool` handles
      overrides, exceptions (→ transient), and empty-vs-error.
- [ ] `PrerequisiteGate` unlocks only on `verified is True` + `customer_id`.
- [ ] `intercept_tool_call` blocks refunds strictly over the limit and redirects.
- [ ] `build_handoff` returns all four fields (None if missing) + `escalated_to`.
- [ ] `wants_human` matches explicit phrases only.
- [ ] `extract_case_facts` pulls amounts/dates/order#/status from message + tool
      results; `decompose_concerns` splits multi-issue messages.
- [ ] `run_support_agent` short-circuits explicit human requests (0 iterations),
      loops on `stop_reason`, applies interception then gate, retries transient /
      explains business errors, flags multi-match clarification, and returns the
      documented dict.
- [ ] `LAB_TARGET=solution uv run pytest lab-22-capstone-support-agent` is green.
