# Lab 23 — Solution notes

## Approach

The pipeline is three layers, each a module, wired by dependency injection so the
tests drive it fully offline with `MockAnthropic`:

1. `schema.py` — the **contract**: the `tool_use` input schema (structural
   guarantee) plus the `Invoice` Pydantic model (semantic guarantee).
2. `extract.py` — **single-document extraction** with few-shot prompting and a
   validation-retry loop that knows when to quit.
3. `batch_pipeline.py` — **scale + reliability**: batch submission by `custom_id`,
   failure-only resubmission with chunking, human-review routing, and per-segment
   accuracy reporting.

## Key decisions & why

- **Nullable *required* fields, not omitted optional ones, for "may be absent"
  data.** Making `stated_total`/`due_date`/`document_type_detail` required but
  `["number","null"]` forces the model to address them on every document while
  letting it answer `null` honestly. Marking them merely optional would let the
  model silently drop them, hiding absence (Task Statement 4.3).

- **`conflict_detected` decides whether a totals mismatch raises.** A sum that
  doesn't match the printed total is *usually* a transcription slip the model can
  fix on retry — so by default it raises and drives the retry. But if the source
  itself is inconsistent, no retry helps; the model flags `conflict_detected=True`,
  validation passes, and the record is routed to a human. This is the 4.4 pattern
  ("`calculated_total` alongside `stated_total`", "`conflict_detected` booleans")
  turned into control flow.

- **Info-absent detection short-circuits the retry loop.** `missing_required_info`
  checks the downstream-required fields *before* validating. A `null` there means
  the information isn't in the document; the loop returns `status="gave_up",
  reason="info_absent"` on the **first** attempt instead of wasting retries. This is
  the exam's central 4.4 insight: retries fix format/structure errors, not absent
  information.

- **Error feedback is appended as extra user turns**, carrying the failed
  extraction JSON *and* the specific validation error, so the follow-up request is
  self-correcting (4.4). The few-shot demonstration turns stay in front (4.2).

- **Batch requests are self-contained single-shot tool calls.** The Batch API can't
  do multi-turn tool calling, so validation-retry happens *after* collection, on
  failures only. Correlation is strictly by `custom_id` (results aren't ordered),
  and oversized docs are chunked into `id#chunk-n` before resubmission (4.5).

- **Routing uses field-level confidence, not a single request score or sentiment.**
  `route_for_review` sends a record to a human if any field is below threshold, a
  conflict is flagged, or required info is absent — exactly the 5.5 triggers.

- **Accuracy is reported by segment.** `accuracy_by_segment` returns `overall`,
  `by_segment`, and `worst_segment` so a strong aggregate can't hide a failing
  document type. The `labeled_set.json` fixture is engineered to make this concrete:
  ~0.92 overall, but `handwritten` at ~0.12.

## Reference walkthrough

- `schema.INPUT_SCHEMA` — `document_type` is the enum-with-`"other"`; `stated_total`,
  `due_date`, `document_type_detail`, `purchase_order_number` are nullable;
  `line_items` and `purchase_order_number` are optional (absent from `required`).
- `Invoice._reconcile_totals` — the model-validator; raises only when
  `abs(calculated_total - stated_total) > TOLERANCE and not conflict_detected`.
- `extract_with_retry` — loop: extract → `missing_required_info` (futile check) →
  `validate_extraction` (retryable check) → append feedback → repeat. Returns a
  status dict with `attempts`, `errors`, `missing_fields`.
- `resubmit_failed` — maps failed ids back to docs, chunks the `oversized` ones,
  rebuilds requests, resubmits. Only failures are resent.
- `route_for_review` / `accuracy_by_segment` — pure functions over records, easy to
  unit-test and to calibrate against a labeled set.

## Common mistakes

- Making absent-able fields *optional* instead of *nullable-required* — the model
  drops them and you lose the signal that data was missing.
- Letting the totals validator raise even when `conflict_detected` is set — you then
  retry forever on a document that is genuinely inconsistent.
- Retrying on info-absent — burns cost and latency for no possible gain. Detect it
  and route to a human/upstream source.
- Indexing batch results by position instead of `custom_id`.
- Resubmitting the whole batch instead of just the failed `custom_id`s.
- Reporting only aggregate accuracy — it hides the weak segment that should keep
  humans in the loop.
- Routing on a single request-level confidence or on sentiment rather than
  calibrated, field-level confidence.

## Checklist

- [ ] Schema has a nullable field, an enum containing `"other"`, and both required
      and optional fields; `build_extraction_tool` returns a copy.
- [ ] `Invoice` reconciles totals and honors `conflict_detected`.
- [ ] `validate_extraction` raises `ValidationError` on a real mismatch.
- [ ] `missing_required_info` flags null downstream-required fields.
- [ ] `extract` forces the tool, assembles few-shot turns, passes null through.
- [ ] `extract_with_retry` retries on semantic errors (feedback appended) and gives
      up immediately on info-absent.
- [ ] Batch: unique `custom_id`, succeeded/failed split, failure-only resubmit with
      chunking.
- [ ] `route_for_review` sends low-confidence/conflict/info-absent to humans.
- [ ] `accuracy_by_segment` exposes the worst segment behind a high aggregate.
- [ ] `LAB_TARGET=solution uv run pytest lab-23-capstone-extraction-pipeline` is green.
