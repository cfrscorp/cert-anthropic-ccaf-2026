# L11 — Solution Notes

## Approach

Four independent, pure(ish) primitives in `hooks.py`, each mapping to one exam
skill:

| Primitive | Hook shape / pattern | Task statement |
|---|---|---|
| `post_tool_use_normalize` | PostToolUse result transformation | 1.5 |
| `intercept_tool_call` | Pre-execution interception gate | 1.5 |
| `PrerequisiteGate` | Programmatic prerequisite / ordering gate | 1.4 / Sample Q1 |
| `build_handoff` | Structured escalation handoff | 1.4 |

Two are stateless functions (`normalize`, `intercept`, `build_handoff`); the gate
is a small stateful class because ordering enforcement inherently needs to
*remember* whether the prerequisite has been satisfied. See
`solution/hooks.py` for the full implementation.

## Key decisions & why

- **Programmatic prerequisite beats prompt/few-shot (Sample Question 1).** The
  scenario's agent skips `get_customer` 12% of the time and refunds the wrong
  account. A stronger system prompt (option B) or more few-shot examples
  (option C) only *lower* a probabilistic failure rate — they can't zero it, and
  a non-zero rate is unacceptable when money moves. `PrerequisiteGate.check`
  returns `False` for `process_refund` until a *verified* customer id is on
  record, so the unsafe path is impossible in code. That is exactly why the
  correct answer to Sample Q1 is A (a programmatic prerequisite), not B/C.

- **Interception blocks; it does not just warn.** `intercept_tool_call` returns a
  structured decision the loop must honor *before* executing the tool. Returning
  `{"action":"block","redirect":"escalate_to_human",...}` both stops the refund
  and names the recovery workflow, so the agent has somewhere to go. A prompt
  ceiling ("never refund over $500") would be probabilistic; the hook is
  deterministic.

- **`> refund_limit`, not `>=`.** The limit is the inclusive auto-approval
  ceiling, so exactly $500 is allowed and $500.01 is blocked. The test uses $600
  (block) and $400 (allow); the configurable-limit test proves the ceiling is a
  parameter, not a constant.

- **Normalize *before* the model sees results.** A `PostToolUse` hook is the right
  place because the transformation must happen every time and must not depend on
  the model noticing that formats differ. Converting to ISO-8601 UTC + status
  labels also makes downstream comparisons (ordering events, retry decisions)
  correct rather than string-comparing `1719921600` against
  `"2024-07-02T12:00:00Z"`.

- **Never mutate the raw result.** `post_tool_use_normalize` copies the input and
  returns a new dict, so a caller keeping the raw result (for logging/audit) is
  unaffected. `test_normalize_does_not_mutate_input` locks this in.

- **Preserve provenance and surface the unknown.** Normalization adds
  `source_tool`; the handoff surfaces missing fields as `None` rather than
  dropping them, so a human sees exactly what is and isn't known. Silent omission
  is worse than an explicit `None`.

- **Verified means verified.** The gate opens only when `get_customer` returns a
  truthy `customer_id` *and* `verified is True`. An ambiguous lookup (no match /
  multiple matches, `verified: False`) leaves the gate closed — matching the
  exam's "multiple matches require clarification, not a heuristic guess."

## Reference walkthrough

**Normalization** — three tools, three representations, one shape:

| Tool | Raw | Canonical |
|---|---|---|
| `tool_a` | `{"timestamp": 1719921600, "status": 200}` | `timestamp="2024-07-02T12:00:00+00:00"`, `status="success"` |
| `tool_b` | `{"timestamp": "2024-07-02T12:00:00Z", "status": "success"}` | same |
| `tool_c` | `{"timestamp": 1719921600, "status": 201}` | same |

**Interception** — `process_refund` at $600 with default limit → `block` +
`escalate_to_human`; at $400 → `{"action":"allow"}`; with `refund_limit=300`,
$400 → `block`. A large amount on `lookup_order` → `allow` (not the refund
policy's concern).

**Prerequisite gate** — fresh gate: `check("process_refund") is False`. After
`record_tool_result("get_customer", {"customer_id":"C-42","verified":True})`:
`check("process_refund") is True` and `verified_customer_id == "C-42"`. A
`verified: False` result leaves it `False`. `get_customer` itself is never gated.

**Handoff** — a full context returns all four fields plus `escalated_to:"human"`;
a sparse context (`{"customer_id":"C-7"}`) returns the rest as `None`.

## Common mistakes

- **Using `>=` for the refund limit**, blocking a legitimate exactly-$500 refund.
- **Blocking with `intercept_tool_call` but omitting `redirect`/`reason`**, so the
  agent has no escalation path or explanation.
- **Mutating the input** in `post_tool_use_normalize` instead of copying.
- **Treating the numeric status as a timestamp** (or vice versa). They are
  separate fields with separate normalizers; a status code is not a time.
- **Opening the gate on any `get_customer` result**, ignoring the `verified`
  flag — this reintroduces the wrong-account bug the gate exists to prevent.
- **Gating the prerequisite tool itself** (`get_customer`), creating a deadlock.
- **Dropping missing handoff fields** instead of surfacing them as `None`.
- **Solving ordering with a prompt** ("always call get_customer first") — that is
  the probabilistic anti-pattern the lab replaces with a code gate.

## Checklist

- [ ] `post_tool_use_normalize` returns a new dict; input is not mutated.
- [ ] Unix int, ISO string (incl. `Z`/naive), and numeric status all normalize.
- [ ] Non-timestamp/status fields are preserved; `source_tool` is added.
- [ ] `intercept_tool_call` blocks `>$500` refunds with `redirect` + `reason`.
- [ ] `refund_limit` is honored as a parameter; non-refund tools are allowed.
- [ ] `PrerequisiteGate` blocks `process_refund` before a verified `get_customer`.
- [ ] Gate opens only on truthy `customer_id` **and** `verified is True`.
- [ ] `build_handoff` returns all four fields + `escalated_to:"human"`; missing → `None`.
- [ ] `uv run pytest lab-11-hooks-and-enforcement` is green.
- [ ] `LAB_TARGET=solution uv run pytest lab-11-hooks-and-enforcement` is green.
