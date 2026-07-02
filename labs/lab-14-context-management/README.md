# L14 — Context Management & Preservation

| | |
|---|---|
| **Task statements** | 5.1 — Preserve critical information across long interactions · 5.4 — Manage context in large exploration sessions |
| **Domain** | 5 — Context Management & Reliability |
| **Difficulty** | 6 / 10 |
| **Estimated effort** | 2:00 |
| **Prerequisites** | L03 — Agentic Loop Fundamentals |

## Objective

Build the context-engineering primitives that keep a long-running agent from
"forgetting" the numbers that matter. You will implement, in `context.py`, four
tools that a customer-support (or codebase-exploration) agent uses to survive
long sessions:

1. `extract_case_facts` — lift transactional facts (amounts, dates, order
   numbers, statuses) out of the raw transcript into a compact, structured
   **case-facts block** you can re-inject into every prompt.
2. `trim_tool_output` — cut a 40-plus-field tool result down to the ~5 fields
   the agent actually needs.
3. `order_for_position` — put a **key-findings summary first**, details after,
   each behind an explicit header, to beat the "lost in the middle" effect.
4. `Scratchpad` + `load_manifest` — persist findings and agent state to a JSON
   file that survives a crash and can be reloaded by a fresh process.

## Background

Long agent sessions degrade in predictable ways. Task Statements 5.1 and 5.4
name the failure modes; this lab builds the countermeasures.

- **Progressive summarization loses the precise stuff.** When conversation
  history is condensed, exact numbers, percentages, dates, and customer-stated
  expectations get blurred: `$45.50` becomes "around $45", `2026-06-22` becomes
  "last week". The fix is to extract those transactional facts into a persistent
  **case-facts block** that lives *outside* the summarized history and is
  re-injected verbatim on every turn.

- **Tool results are token hogs.** An `lookup_order` call can return 40+ fields
  when only 5 are relevant to a return. Left unchecked, these verbose blobs
  accumulate in context and crowd out everything else. Trim them to the relevant
  fields *before* they land in history.

- **"Lost in the middle."** Models reliably attend to the **beginning and end**
  of a long input but drop content buried in the middle. So aggregate results
  with a **summary of key findings at index 0** and give every detailed section
  an explicit header — don't bury conclusions.

- **Context degrades; disk does not.** In extended sessions models start giving
  inconsistent answers and referencing "typical patterns" rather than the
  specific facts discovered earlier. A **scratchpad file** persists key findings
  across context boundaries, and a **manifest** of structured agent state lets a
  coordinator resume after a crash instead of re-exploring from scratch. (The
  companion techniques — subagent delegation to isolate verbose exploration, and
  `/compact` — are covered in the Stretch goals.)

## Tasks

Edit `starter/context.py` so it matches the public API of
`solution/context.py`. The fixtures `sample_conversation.json` and
`sample_order_lookup.json` in the lab root drive the tests.

### 1. `extract_case_facts(conversation) -> dict`

Scan every message and return a dict with four lists — `amounts`, `dates`,
`order_numbers`, `statuses` — of de-duplicated, first-seen-order string values.

- Messages may be plain strings or dicts with a `content` field (string or a
  list of content blocks).
- Use regexes: amounts (`$129.99`), ISO/slash dates (`2026-06-15`), order ids
  (`A-10432`, `ORD-77219` — letters, a dash, then ≥3 digits; the `#` prefix is
  *not* part of the id). Match statuses against a known vocabulary (shipped,
  delivered, in transit, refund, pending, ...).

### 2. `trim_tool_output(raw, relevant_fields) -> dict`

Return a new dict with only the requested top-level keys that exist in `raw`,
in the order given. Silently skip keys that aren't present — don't raise.

### 3. `order_for_position(sections, *, summary_header="Key Findings") -> list`

Given sections (each a dict with `title`, `summary`, `detail`), return a list of
`{"header", "body"}` dicts where **index 0** is a summary section whose body
lists every section's title and one-line summary, followed by one entry per
detailed section (`header` = title, `body` = detail).

### 4. `Scratchpad` + `load_manifest`

- `Scratchpad(path)` — load existing JSON state on construction.
- `record(key, value)` — store and **flush to disk immediately** (so a crash
  loses nothing). Prefer an atomic write (temp file + `os.replace`).
- `recall(key, default=None)` — return the stored value.
- `load_manifest(path)` — parse and return a JSON manifest dict.

The persistence contract is the point: after `record`, a **brand-new**
`Scratchpad` pointed at the same path must `recall` the value.

## Deliverables

- `starter/context.py` implementing the public API above.
- All tests in `tests/test_lab14.py` green against your `starter/`.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-14-context-management                     # your work (starter/)
LAB_TARGET=solution uv run pytest lab-14-context-management # reference — always green
```

The tests check that case facts retain the exact numeric / date / order / status
values; that `trim_tool_output` returns only the requested fields from the 40+
field fixture; that `order_for_position` puts the summary at index 0 with headers
on every section; that a `Scratchpad` value written by one instance is recalled
by a fresh one; and that `load_manifest` round-trips a JSON manifest.

## Stretch goals

- **Provenance.** Extend `extract_case_facts` to record which message index each
  fact came from, so a downstream agent can cite the source turn.
- **Nested trimming.** Let `trim_tool_output` accept dotted paths
  (`"customer.email"`) to pull fields out of nested tool results.
- **Render the block.** Add a helper that formats the case-facts dict as a
  Markdown block suitable for prepending to a system prompt each turn.
- **Subagent isolation.** Sketch how you'd run the verbose `lookup_order`
  exploration in a subagent that returns only the trimmed fields, keeping the
  coordinator's context clean (Task Statement 5.4).
- **`/compact` vs. facts block.** Write a short note on when `/compact` suffices
  and when you still need an explicit case-facts block (hint: `/compact`
  summarizes — and summaries lose numbers).
