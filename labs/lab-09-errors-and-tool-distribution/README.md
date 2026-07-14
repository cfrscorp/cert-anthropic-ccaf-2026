# L09 — Structured Error Responses & Tool Distribution

| | |
|---|---|
| **Task statements** | 2.2 — Implement structured error responses for MCP tools · 2.3 — Distribute tools appropriately across agents and configure tool choice |
| **Domain** | 2 — Tool Design & MCP Integration |
| **Difficulty** | 5 / 10 |
| **Estimated effort** | 2:00 |
| **Prerequisites** | L03 — Agentic Loop · L05 — Tool Interface Design |

## Objective

Make an agent's tools **legible** in two dimensions:

1. **When a tool fails**, return *structured* error metadata — an MCP-style
   `{isError, errorCategory, isRetryable, message}` object — so the agent (or a
   coordinator) can decide whether to retry, explain a policy limit to the user,
   or propagate partial results. No more uniform `"Operation failed"`.
2. **When you wire an agent up**, give it only the tools its role needs (4-5, not
   18), add narrow cross-role tools for high-frequency needs, and set
   `tool_choice` correctly for the situation.

You will implement two small, importable modules and prove the behaviour with
deterministic tests.

## Background

### Structured Errors (Task Statement 2.2)

The MCP `isError` flag tells the agent a tool call failed. But a bare failure
signal — or a uniform `"Operation failed"` string — leaves the agent blind: it
cannot tell a timeout (retry!) from a policy violation (do NOT retry; explain to
the user). The fix is to return **structured metadata** the model can reason
about:

```json
{
  "isError": true,
  "errorCategory": "business",
  "isRetryable": false,
  "message": "Refund of $750 exceeds the $500 auto-approval limit."
}
```

Four categories, and **only the first is retryable**:

| Category | Examples | `isRetryable` |
|---|---|:---:|
| `transient` | timeout, service unavailable, connection reset | **true** |
| `validation` | invalid / malformed input, missing required field | false |
| `business` | policy violation (refund over limit), disallowed action | false |
| `permission` | caller not authorized, 401/403 | false |

Two more distinctions the task statement calls out:

- **Retryable vs non-retryable.** Returning `isRetryable: false` for validation,
  business, and permission errors stops the agent wasting retries on failures
  that will never succeed with the same input.
- **Access failure vs valid empty result.** "The search ran and found nothing"
  (`empty`) is a *successful* answer, not an error. "The search backend was
  unreachable" (`access_failure`) is a failure needing a decision. Silently
  returning empty-as-success hides real failures — an anti-pattern (Task 5.3,
  Sample Question 8).

### Tool Distribution & tool_choice (Task Statement 2.3)

- **Too many tools degrades selection.** Handing one agent 18 tools instead of
  the 4-5 it needs increases decision complexity and misrouting. Scope each
  subagent to its role.
- **Out-of-specialization tools get misused.** A synthesis agent handed web
  tools will try to run searches. Don't give it the option.
- **Scoped cross-role tools.** For a *high-frequency* need (Sample Question 9:
  synthesis constantly needs simple fact-checks), give a narrow tool like
  `verify_fact` — and route the rare complex cases through the coordinator.
- **`tool_choice`** has three settings:

  | Setting | Meaning | Use when |
  |---|---|---|
  | `"auto"` | may call a tool **or** answer in text | conversational turn |
  | `"any"` | **must** call *some* tool (model picks) | need structured output; document type / schema unknown |
  | `{"type": "tool", "name": "..."}` | **must** call that specific tool | force one tool first (e.g. `extract_metadata` before enrichment) |

## Tasks

Edit the two modules in `starter/`. Keep the same public API as `solution/`.

### `errors.py`

1. `is_retryable(category) -> bool` — `True` only for `transient`; raise
   `ValueError` for unknown categories.
2. `make_error(category, message, *, retryable=None) -> dict` — return
   `{"isError": True, "errorCategory": category, "isRetryable": <bool>,
   "message": message}`. Default `isRetryable` to `is_retryable(category)`;
   validate the category and require a non-empty message.
3. `classify(exc_or_kind) -> str` — map an exception (`TimeoutError`,
   `PermissionError`, `ValueError`, …) or a free-form string ("timeout", "policy
   violation") onto one of the four categories. Always return a valid category.
4. `is_empty_result_vs_failure(result) -> str` — return `"access_failure"` for an
   error object / error status / `None`; `"empty"` for a successful query with
   zero matches; `"results"` otherwise.

### `tool_distribution.py`

`ALL_RESEARCH_TOOLS` (the full 18-tool catalogue for the Scenario 3 research
system) is provided. Design `ROLE_TOOLS` yourself.

1. `ROLE_TOOLS` — map each role (`coordinator`, `searcher`, `analyst`,
   `synthesis`, `writer`) to the 4-5 tool names it needs. Keep `verify_fact` out
   of the base `synthesis` set (it's added as a cross-role tool). Do **not**
   assign the deprecated generic `fetch_url` — it was replaced by
   `load_document`.
2. `assign_tools(role, all_tools) -> list` — return only the tools scoped to
   `role`. Raise `ValueError` for an unknown role.
3. `is_overprovisioned(tools) -> bool` — flag a set larger than
   `MAX_RECOMMENDED_TOOLS` (the full 18-tool set is over-provisioned; a scoped
   4-5 tool set is not).
4. `add_scoped_cross_role_tool(agent, tool) -> dict` — add an allow-listed
   cross-role tool (e.g. `verify_fact` for `synthesis`); raise `ValueError` for a
   tool that isn't allow-listed for that role. Idempotent.
5. `choose_tool_choice(scenario) -> object` — `"auto"` for conversational,
   `"any"` for unknown-schema / guarantee-a-tool-call, and
   `{"type": "tool", "name": "extract_metadata"}` to force
   `extract_metadata` first.
6. `run_forced_tool_call(client, scenario, messages, tools, ...)` — compute the
   `tool_choice` and forward it to `client.messages.create(...)`. The `client`
   is **injected** so tests can pass a `MockAnthropic` (see L03).

## Deliverables

- `starter/errors.py` and `starter/tool_distribution.py` implemented (matching
  the public API in `solution/`).
- All tests in `tests/test_lab09.py` passing against your `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-09-errors-and-tool-distribution                    # your work (starter/)
LAB_TARGET=solution uv run pytest lab-09-errors-and-tool-distribution  # reference — always green
```

The tests assert that error objects carry `isError` / `errorCategory` /
`isRetryable` / `message`; that transient is retryable and business is not; that
empty results are distinguished from access failures; that `assign_tools`
restricts to a role and excludes other roles' tools; that `is_overprovisioned`
flags the 18-tool catalogue and clears a scoped set; that `choose_tool_choice`
maps the canonical scenarios; and — via `MockAnthropic` — that a forced
`tool_choice` is actually forwarded to the API call.

## Stretch Goals

- **Local recovery then propagate (Task 5.3).** Write a small
  `subagent_call(...)` that retries `transient` errors locally (bounded) and only
  returns a structured error to the "coordinator" when it cannot recover —
  including what was attempted and any partial results.
- **Coverage-annotated propagation.** Have a mock synthesis step return findings
  plus a `coverage` note marking which topics have gaps because a source was an
  `access_failure` (not merely `empty`).
- **`"any"` in the loop.** Extend `run_forced_tool_call` (or add a sibling) that
  uses `tool_choice: "any"` and assert with `MockAnthropic` that the model is
  forced to return a `tool_use` block rather than conversational text.
- **Customer-facing messages.** For each `business` error, add a
  customer-friendly `message` and confirm it never leaks internal identifiers.
