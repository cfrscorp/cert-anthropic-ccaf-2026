# Lab 23 — Capstone: Structured Data Extraction Pipeline

**Scenario 6 (Structured Data Extraction) · Preparation Exercise 3 · Difficulty 8/10 · Est. 3:00**
**Prerequisites: L10 (validation & retry), L17 (batch processing), L18 (human review & confidence)**

> Capstone lab. It integrates the structured-output, validation-retry, batch, and
> human-review concepts from earlier labs into one production-shaped pipeline.
> The lab is **self-contained** — everything is reimplemented inside this folder;
> you do not import other labs.

## Objective

Build the extraction pipeline described in Scenario 6: pull structured data from
messy, varied documents; guarantee schema-shaped output with `tool_use`; validate
semantics with Pydantic; retry intelligently with error feedback (and recognise
when a retry is futile); process documents in bulk with the Message Batches API;
and route the risky extractions to humans using calibrated, field-level confidence
and per-segment accuracy reporting.

This exercises Task Statements **4.2** (few-shot), **4.3** (tool_use + JSON schema),
**4.4** (validation/retry/feedback), **4.5** (batch processing), and **5.5** (human
review & confidence calibration).

## Background

A strict JSON schema delivered through `tool_use` removes *syntax* errors — the
model can't emit malformed JSON or the wrong shape. It does **not** remove
*semantic* errors: line items that don't sum to the total, a value in the wrong
field, or a total the document never actually stated. Production extraction systems
layer several defenses:

- **Schema design** — nullable required fields so the model returns `null` instead
  of fabricating; an `enum` with an `"other"` + detail escape hatch for extensible
  categories; required vs optional fields.
- **Semantic validation** — a Pydantic model that reconciles `calculated_total`
  (from line items) against the model-reported `stated_total`, and distinguishes a
  *transcription* mismatch (retryable) from a *genuinely inconsistent source*
  (`conflict_detected` → route to a human).
- **Retry with feedback** — append the failed extraction and the specific error to
  the next request. But retries are wasted when the information is simply **absent**
  from the source; detect that and stop.
- **Few-shot examples** — demonstrate correct extraction across varied layouts
  (narrative, tabular, receipts, the `"other"`/null case, a flagged conflict).
- **Batch processing** — `custom_id`-keyed requests, ~50% cheaper, up to 24h with no
  SLA; resubmit only the failures, chunking any that exceeded the context limit.
- **Human-review routing** — a 97% *aggregate* accuracy can hide a document type
  that's failing badly. Route low field-confidence / ambiguous / info-absent
  extractions to humans, and report accuracy **by segment** to catch the weak slice.

## Tasks (integrative)

Implement the same public API in `starter/` that the reference `solution/` exposes.
Each module builds on the previous one.

### `schema.py` — the contract
1. `build_extraction_tool()` — return a tool whose `input_schema` has at least one
   **nullable** field (type list containing `"null"`), an **enum with `"other"`**,
   plus a mix of required and optional fields. Return a copy.
2. `Invoice` (Pydantic) — declare the fields, expose a `calculated_total` property,
   and a `model_validator` that **raises** on a totals mismatch **unless**
   `conflict_detected` is `True`.
3. `validate_extraction(data)` → `Invoice` (raises `ValidationError`).
4. `missing_required_info(data)` → the downstream-required fields that are null (the
   *info-absent* signal).

### `extract.py` — extraction + retry
5. `build_few_shot_messages()` and `build_messages(document, *, error_feedback, few_shot)`.
6. `extract(client, doc, *, tool_choice=None, error_feedback=None, few_shot=True)` —
   force the extraction tool by default; return the `tool_use` input dict.
7. `extract_with_retry(client, doc, max_retries=2)` — validate; on a **semantic**
   failure append the error and retry; on **info-absent** give up *immediately*
   (don't burn retries). Return a status dict.

### `batch_pipeline.py` — scale + reliability
8. `build_requests` / `submit_and_collect` / `resubmit_failed` — `custom_id`
   correlation; resend only failures; chunk any `oversized` document.
9. `choose_api` / `submission_frequency` — batch-vs-sync and SLA math.
10. `route_for_review(records, *, confidence_threshold=0.75)` — send low-confidence,
    conflict, and info-absent extractions to human review.
11. `accuracy_by_segment(records, *, segment_field, fields)` — field-level accuracy
    overall and per segment, exposing the `worst_segment`.

## Deliverables

- Completed `starter/schema.py`, `starter/extract.py`, `starter/batch_pipeline.py`
  with all tests green.
- Keep dependency injection: every Claude-calling function takes a `client`.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-23-capstone-extraction-pipeline
```

The reference solution is validated with:

```bash
LAB_TARGET=solution uv run pytest lab-23-capstone-extraction-pipeline -q
```

`docs/` holds the fixtures the tests and demos use: `clean_invoice.txt`,
`total_mismatch_invoice.txt`, `info_absent_invoice.txt`, `oversized_ledger.txt`,
three document-type samples (`clean_invoice`, `pos_receipt`, `purchase_order`), and
`labeled_set.json` — a labeled set engineered so overall accuracy is high (~0.92)
while the `handwritten` segment is quietly failing (~0.12).

## Stretch goals

- Add a `field_confidence` object to the tool schema so the model self-reports
  per-field confidence, then calibrate `route_for_review`'s threshold against
  `labeled_set.json`.
- Implement **stratified random sampling** of high-confidence extractions for
  ongoing error-rate monitoring (5.5) — sample a fixed fraction per segment with a
  seeded RNG.
- Extend `resubmit_failed` to correlate chunk results back to the parent document
  and merge line items across chunks.
- Add a `conflict_detected` few-shot example for a *credit note* to show the enum's
  `"other"` path and negative totals together.
