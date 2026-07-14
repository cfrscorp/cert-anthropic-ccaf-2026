# L20 — Error Propagation & Provenance in Synthesis

| | |
|---|---|
| **Task statements** | 5.3 — Error propagation across multi-agent systems · 5.6 — Provenance & uncertainty in multi-source synthesis |
| **Domain** | 5 — Context Management & Reliability |
| **Difficulty** | 7 / 10 |
| **Estimated effort** | 2:00 |
| **Prerequisites** | L19, L09 |

## Objective

Build the two mechanisms that keep a multi-agent research system honest when
things go wrong and when sources disagree:

1. **Error propagation (5.3)** — when a subagent fails, hand the coordinator
   *structured error context* (failure type, attempted query, partial results,
   alternatives) so it can recover intelligently. Recover transient failures
   locally; propagate only what you cannot resolve — never suppress an error as
   "success", never terminate the whole workflow over one failure.
2. **Provenance (5.6)** — carry every claim's source through synthesis, keep
   conflicting statistics from credible sources *both* (annotated, not resolved),
   attach publication dates so time differences aren't misread as contradictions,
   and render each content type in its natural form.

You are not calling a live agent. The point is the *contract* around the agents —
the structured payloads and merge/annotate logic your code owns.

## Background

### Error Propagation (Task 5.3, Sample Question 8)

A web-search subagent times out mid-research. How that failure reaches the
coordinator determines whether the run can recover. Four options (Sample Q8):

- **A — structured error context** (failure type, attempted query, partial
  results, alternatives). Correct: the coordinator can retry with a modified
  query, try an alternative source, or proceed with partial results.
- **B — generic "search unavailable"** after silent retries. Hides the context
  the coordinator needs.
- **C — return empty results marked successful.** Suppresses the failure; the
  report is silently incomplete and no recovery is possible.
- **D — propagate the exception to a top handler that kills the run.** Terminates
  the whole workflow when recovery could have succeeded.

Two failure *shapes* must never be confused:

- **Access failure** — the query never completed (timeout, connection reset).
  The answer is *unknown*; it is retry-worthy.
- **Empty success** — the query completed and legitimately found nothing.
  Retrying is pointless; the emptiness *is* the answer.

A subagent should implement **local recovery** for transient failures (retry in
place) and only **propagate** what it cannot resolve — always carrying what it
attempted and any partial results. Synthesis output then gets **coverage
annotations**: which topics are well-supported vs. which are gaps because a source
was unavailable.

### Provenance & Uncertainty (Task 5.6)

Synthesis compresses many findings into one report, and naive summarization
quietly:

- **drops sources** — keeps the sentence, loses the URL/doc/excerpt. Fix:
  preserve **claim → source** mappings and *merge* them through synthesis.
- **picks a winner** when two credible sources give different statistics. Fix:
  keep **both** values, each attributed, and mark the conflict unresolved for the
  coordinator/human to reconcile.
- **misreads time as contradiction** — a 2023 figure and a 2024 figure look like
  a conflict. Fix: require **publication/collection dates** on every value.
- **flattens format** — turns tables and lists into uniform prose. Fix: render
  **financial as tables, news as prose, technical findings as lists**.

## Tasks

Implement two modules under `starter/` so their public APIs match `solution/`.

### `starter/propagation.py`

1. `build_error_context(failure_type, attempted, partial_results, alternatives)`
   → a dict with **all four** fields always present (empty lists when none).
2. `classify_result(result)` → `"access_failure"` (error/timeout),
   `"empty_success"` (completed, no matches), or `"success"` (returned data).
3. `handle_subagent_failure(error)` → recover transient failures locally
   (`recovered_locally: True`); propagate hard failures (and retry-exhausted
   transients) with partial results attached.
4. `coverage_annotations(findings)` → `{"well_supported": [...], "gaps": [...]}`.

### `starter/provenance.py`

5. `merge_claims(findings)` → flat list of `{"claim", "source"}`, every claim
   keeping its source; a per-claim `source` overrides the finding's default.
6. `annotate_conflict(values)` → keep **both** values with attribution,
   `conflict`/`resolved` flags; do **not** pick one.
7. `needs_temporal_flag(claims)` → True if a quantitative claim lacks a date;
   `attach_dates(claim, date)` → a dated copy (non-mutating).
8. `render_by_type(content_type, data)` → financial→table, news→prose,
   technical→list; `ValueError` for anything else.

## Deliverables

- `starter/propagation.py` and `starter/provenance.py` implemented to match the
  public APIs in `solution/`.
- All tests in `tests/test_lab20.py` passing against your `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-20-error-propagation-provenance                     # your work (starter/)
LAB_TARGET=solution uv run pytest lab-20-error-propagation-provenance # reference (always green)
```

The tests assert: `build_error_context` has all four fields; `classify_result`
distinguishes a timeout from an empty-but-successful query;
`handle_subagent_failure` recovers a transient failure locally and propagates a
hard failure **with** partial results; `merge_claims` preserves each claim's
source (from `findings.json`); `annotate_conflict` retains **both** conflicting
values with attributions; and `render_by_type` picks the right format per content
type.

## Stretch Goals

- **Reconciliation policy.** Add a function that, given an annotated conflict,
  *recommends* (not decides) a reconciliation when publication dates differ —
  e.g. "values differ but so do collection dates; likely temporal, not
  contradictory."
- **Provenance-aware report.** Combine `merge_claims` + `coverage_annotations`
  into a single synthesis report string with a "well-established" vs. "contested"
  section and inline citations.
- **Retry budget.** Extend `handle_subagent_failure` to decrement a retry counter
  and only recover locally while budget remains, propagating once exhausted.
- **Mixed-format render.** Add a `render_report(sections)` that dispatches each
  section through `render_by_type` so one report mixes tables, prose, and lists.
