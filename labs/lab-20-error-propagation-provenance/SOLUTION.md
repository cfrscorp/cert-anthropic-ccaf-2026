# L20 — Solution notes

## Approach

Two small, offline modules model the *contracts* between subagents, coordinator,
and the synthesis step. There is no live model call; the reliability behavior
lives in structured payloads and merge/annotate logic that your code owns, so it
can be asserted deterministically.

- `propagation.py` — how a failure travels from a subagent to the coordinator.
- `provenance.py` — how attribution, conflict, dates, and format survive
  synthesis.

## Key decisions & why

### Structured error context beats the three wrong answers (Sample Q8)

Sample Question 8 contrasts one right approach with three anti-patterns, and this
lab encodes exactly that contrast:

- **Structured context (correct, answer A).** `build_error_context` always
  returns `failure_type`, `attempted`, `partial_results`, and `alternatives` —
  even when empty — so the coordinator has everything it needs to *decide*: retry
  with a modified query, switch sources, or proceed with partials. A generic
  status (answer B, "search unavailable") throws that information away.
- **Never suppress-as-success (answer C).** `classify_result` keeps
  `"access_failure"` and `"empty_success"` as distinct return values. Collapsing
  them — returning empty results marked successful — is the exact failure mode C
  describes: the coordinator proceeds believing "nothing was found" when really
  "we never found out," and the report is silently incomplete.
- **Never terminate-all (answer D).** `handle_subagent_failure` returns a payload;
  it never raises. One subagent's timeout produces a recovered result or a
  propagated context — it does not crash the workflow.

### Local recovery vs. propagation

Transient failures (`timeout`, `rate_limit`, `service_unavailable`,
`connection_reset`) are momentary, so the subagent retries **in place** and the
coordinator never sees them. Everything else — permission errors, malformed
queries, not-found — will fail identically on retry, so it is propagated
immediately with partial results attached. A transient failure whose retry budget
is exhausted (`retries_exhausted`) is *also* propagated: local recovery is a first
resort, not an infinite loop. The distinction between "recover" and "propagate" is
surfaced as `recovered_locally: True/False` so the coordinator can log and reason
about it.

### Why conflicts are annotated, not resolved

When two credible sources report different statistics, arbitrarily picking one
destroys information and can be simply wrong. `annotate_conflict` keeps **both**
values with their source attribution and sets `resolved: False`. Reconciliation
is a *coordinator/human* decision made with full information — and often the
"conflict" dissolves once you look at the dates (see next point). Picking a winner
inside a summarizer hides both the disagreement and the reason for it.

### Temporal data is not contradiction

The fixture's two sources report 18% (IEA, 2024) and 14% (BloombergNEF, 2023).
These are not contradictory — they are measurements from different years. That is
why every value carries a `date`, `needs_temporal_flag` catches undated
statistics, and the conflict note explicitly says to check dates before treating
a difference as a contradiction.

### Render by type, not uniformly

Financial data as a table, news as prose, technical findings as a list.
`render_by_type` dispatches on `content_type` and raises `ValueError` for
anything unknown rather than silently defaulting — an unknown type is a bug in the
caller, and a silent default would flatten format the way naive synthesis does.

## Reference walkthrough

- **`build_error_context`** normalizes `partial_results`/`alternatives` to lists
  and always includes all four fields plus `status: "error"`.
- **`classify_result`** checks error/timeout signals *first* (`status == "error"`,
  `error`, `isError`, `failure_type`, `timed_out`) → `access_failure`; otherwise
  looks at `results`/`data` → `empty_success` when empty, else `success`.
- **`handle_subagent_failure`** branches on `failure_type ∈ TRANSIENT_FAILURES`
  and `retries_exhausted`: recover locally (return `status: "recovered"`) or reuse
  `build_error_context` to propagate with `recovered_locally: False`.
- **`coverage_annotations`** partitions findings — sources present and no failure
  marker → `well_supported`; otherwise a `gap` with a reason.
- **`merge_claims`** flattens findings, letting a per-claim `source` override the
  finding's default, and keeps a per-claim `date` when present.
- **`annotate_conflict`** retains every value with attribution and flags a
  conflict only when distinct values exist (order-preserving, no hashing).
- **`needs_temporal_flag` / `attach_dates`** flag undated quantitative claims and
  return dated *copies* (non-mutating).
- **`render_by_type`** → `_render_table` (markdown), `_render_prose` (joined
  paragraph), `_render_list` (`- ` bullets).

## Common mistakes

- Returning empty results as "success" — conflating `access_failure` with
  `empty_success`. The whole point of 5.3 is to keep them distinct.
- Raising in `handle_subagent_failure` — that recreates the terminate-all
  anti-pattern (answer D). Return a payload.
- Dropping `partial_results` when propagating a hard failure — the coordinator may
  still be able to use them.
- Picking one value in `annotate_conflict` — the exam explicitly wants both,
  attributed.
- Mutating the input in `attach_dates` — return a copy.
- Losing `source` in `merge_claims` — the mapping is the deliverable.
- Defaulting an unknown `content_type` to prose instead of raising.

## Checklist

- [ ] `build_error_context` returns all four fields, empty lists by default.
- [ ] `classify_result` distinguishes access failure / empty success / success.
- [ ] `handle_subagent_failure` recovers transient locally, propagates hard
      failures (and exhausted transients) with partial results, never raises.
- [ ] `coverage_annotations` splits well-supported topics from gaps.
- [ ] `merge_claims` preserves each claim's source; per-claim source wins.
- [ ] `annotate_conflict` keeps both values + attribution, `resolved: False`.
- [ ] `needs_temporal_flag` / `attach_dates` handle dates (non-mutating).
- [ ] `render_by_type` → table / prose / list; `ValueError` otherwise.
- [ ] `uv run pytest lab-20-error-propagation-provenance` green on `starter/`.
- [ ] `LAB_TARGET=solution uv run pytest lab-20-error-propagation-provenance`
      green.
