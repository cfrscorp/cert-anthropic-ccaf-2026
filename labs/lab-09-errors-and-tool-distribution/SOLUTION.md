# L09 — Solution Notes

## Approach

Two independent, importable modules — no live Claude call is needed for the core
logic, which keeps the tests fast and deterministic.

- **`errors.py`** centralises the category → retryable policy in one table
  (`_RETRYABLE`). `make_error` is the single constructor for the MCP error shape;
  `is_retryable` reads the table; `classify` maps exceptions/strings onto a
  category; `is_empty_result_vs_failure` inspects a result payload's shape.
- **`tool_distribution.py`** models the Scenario 3 research system.
  `ALL_RESEARCH_TOOLS` is the full 18-tool catalogue; `ROLE_TOOLS` is the scoped
  per-role assignment; `assign_tools` filters the catalogue to a role;
  `is_overprovisioned` compares against `MAX_RECOMMENDED_TOOLS`;
  `add_scoped_cross_role_tool` guards a tiny allow-list; `choose_tool_choice`
  maps scenarios to `tool_choice`; `run_forced_tool_call` proves the choice
  reaches the injected client.

See `solution/errors.py` and `solution/tool_distribution.py` for the full code.

## Key decisions & why

- **Why a generic `"Operation failed"` is an anti-pattern.** It collapses four
  very different failures into one opaque signal. The agent can't tell a timeout
  (retry) from a `$500`-limit violation (explain, don't retry) from bad input
  (fix the input) from an authorization gap (escalate). Structured metadata —
  `errorCategory` + `isRetryable` + a human-readable `message` — restores the
  agent's ability to make the right recovery decision. This is exactly what Task
  Statement 2.2 asks for.

- **Why only `transient` is retryable.** A timeout or "service unavailable" may
  succeed on a second attempt. Validation, business, and permission failures will
  *not*: the same invalid input, the same over-limit refund, the same
  unauthorized caller will fail identically. Marking them `isRetryable: false`
  prevents wasted retry loops. (`retryable=` lets you override — e.g. a transient
  error whose retry budget is already spent.)

- **Why `"search unavailable"` (a generic empty/error) is an anti-pattern.** A
  valid empty result ("the query ran; there were no matches") and an access
  failure ("the query could not run") demand opposite responses: accept the empty
  answer vs retry/route around the failure. Collapsing them — or, worse, returning
  an empty list *marked successful* when the backend actually failed — hides the
  failure from the coordinator and silently corrupts the research output (Sample
  Question 8; Task 5.3). `is_empty_result_vs_failure` keeps the two separate, and
  treats a bare `None` as a failure to surface rather than an answer.

- **Why 18 tools hurts.** Tool selection scales badly with tool count: more
  near-neighbour tools means more opportunities to misroute, and the model is more
  likely to reach for a tool outside its lane (a synthesis agent attempting a web
  search). Scoping each subagent to the 4-5 tools its role needs is the single
  biggest reliability lever here (Task 2.3). `is_overprovisioned` encodes the
  rule of thumb; `assign_tools` enforces the scoping.

- **Why a *scoped* cross-role tool, not "give synthesis all web tools."** Sample
  Question 9: 85% of synthesis verifications are simple fact-checks. A narrow
  `verify_fact` tool covers the common case with least privilege; the 15% complex
  cases still route through the coordinator. `add_scoped_cross_role_tool` enforces
  an allow-list so an agent can't quietly re-accumulate the whole catalogue and
  become over-provisioned again. Handing it the full `web_search` tool (option C
  in the exam) is the over-provisioning trap — the guard raises `ValueError`.

- **Why replace `fetch_url` with `load_document`.** A generic `fetch_url` fetches
  anything; the constrained `load_document` validates document URLs (allow-listed
  hosts). Per Task 2.3, no role is assigned the deprecated generic tool.

- **`tool_choice` mapping.** `"auto"` when a text answer is acceptable
  (conversational); `"any"` to *guarantee* a tool call when the document type or
  schema is unknown and any of several extraction tools would do; forced
  `{"type": "tool", "name": ...}` to run one specific tool first (e.g.
  `extract_metadata` before enrichment), then continue in follow-up turns.

## Reference walkthrough

**Errors.** `make_error("business", "Refund of $750 exceeds the $500 limit.")` →
`{"isError": True, "errorCategory": "business", "isRetryable": False, "message":
"Refund of $750 exceeds the $500 limit."}`. `classify(TimeoutError())` →
`"transient"`; `classify("policy violation")` → `"business"`.
`is_empty_result_vs_failure({"results": []})` → `"empty"`;
`is_empty_result_vs_failure(make_error("transient", "..."))` → `"access_failure"`.

**Tools.** `assign_tools("synthesis", ALL_RESEARCH_TOOLS)` →
`[synthesize_findings, detect_coverage_gaps, format_citations]` (no `web_search`).
`is_overprovisioned(ALL_RESEARCH_TOOLS)` → `True` (18 > 7);
`is_overprovisioned(<scoped set>)` → `False`. Adding the cross-role tool:

```python
agent = {"role": "synthesis", "tools": assign_tools("synthesis", ALL_RESEARCH_TOOLS)}
agent = add_scoped_cross_role_tool(agent, "verify_fact")   # ok — allow-listed
add_scoped_cross_role_tool(agent, "web_search")            # ValueError — not allow-listed
```

**tool_choice forwarding.** `run_forced_tool_call(client,
"force_extract_metadata_first", messages, tools)` calls
`client.messages.create(..., tool_choice={"type": "tool", "name":
"extract_metadata"})`; the test reads `client.calls[-1]["tool_choice"]` to prove
it was forwarded.

## Common mistakes

- Returning `{"error": "failed"}` or a bare string instead of the four-field MCP
  shape. Tests assert the exact keys and `isError is True`.
- Marking `business` / `validation` / `permission` errors retryable (or forgetting
  that `transient` *is* retryable).
- Treating an access failure as an empty result (or vice versa) — and treating
  `None` as a valid empty answer instead of a failure.
- Letting `classify` return something outside the four categories, or crashing on
  an unrecognised input instead of falling back to a category.
- Building `ROLE_TOOLS` with 8+ tools per role (still over-provisioned), or
  leaking another role's tools into a role (e.g. `web_search` in `synthesis`).
- Assigning the deprecated `fetch_url` to any role instead of `load_document`.
- Letting `add_scoped_cross_role_tool` accept any tool — it must reject tools not
  on the per-role allow-list.
- Returning a *string* like `"forced"` from `choose_tool_choice` instead of the
  actual `{"type": "tool", "name": ...}` object the API expects.
- Constructing a real `anthropic.Anthropic()` inside `run_forced_tool_call`
  instead of using the injected `client` (breaks the `MockAnthropic` test).

## Checklist

- [ ] `make_error` returns exactly `{isError, errorCategory, isRetryable, message}`.
- [ ] `is_retryable`: `transient` → True; validation/business/permission → False.
- [ ] `classify` maps exceptions and strings to one of the four categories, always.
- [ ] `is_empty_result_vs_failure` separates `empty`, `results`, and `access_failure`.
- [ ] `ROLE_TOOLS` scopes each role to 4-5 tools; no `fetch_url`; `verify_fact`
      not in the base synthesis set.
- [ ] `assign_tools` restricts to role and raises on unknown roles.
- [ ] `is_overprovisioned` flags 18 and clears a scoped set.
- [ ] `add_scoped_cross_role_tool` allow-lists `verify_fact` for synthesis and
      rejects the rest; idempotent.
- [ ] `choose_tool_choice`: conversational → `"auto"`, unknown schema → `"any"`,
      force → `{"type": "tool", "name": "extract_metadata"}`.
- [ ] `run_forced_tool_call` forwards `tool_choice` via the injected client.
- [ ] `LAB_TARGET=solution uv run pytest lab-09-errors-and-tool-distribution` is green.
