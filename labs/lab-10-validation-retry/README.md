# Lab 10 — Validation, Retry & Feedback Loops

| | |
|---|---|
| **Exam mapping** | Task Statement 4.4 |
| **Difficulty** | 5 / 10 |
| **Estimated time** | 1:45 |
| **Prerequisites** | L04 (Structured Output via `tool_use`) |

## Objective

L04 gave you *syntactically* guaranteed output: a tool's `input_schema` removes
malformed JSON, missing keys, and wrong types. This lab tackles the half a schema
**cannot** guarantee — *semantic* correctness — and the loop that fixes it:

- Validate an extraction with a **Pydantic v2** model that flags a
  `calculated_total` vs `stated_total` mismatch and other source conflicts.
- Retry **with error feedback**: append the *specific* validation error (plus the
  failed extraction and the original document) to the next request so the model
  can self-correct — not a vague "try again".
- Know **when a retry is futile**: retries fix *format* and *structural* errors,
  but not information that is *absent from the source* or a *source that
  contradicts itself*. Give up (or escalate) instead of looping pointlessly.
- Attach a `detected_pattern` label to each finding so dismissal / false-positive
  rates can be analysed across many documents.

## Background

A strict schema eliminates **syntax** errors. It says nothing about **meaning**:
nothing in a JSON Schema guarantees the `line_items` sum to `stated_total`, that a
value landed in the right field, or that two dates are consistent. Those are
*semantic* errors, and they are exactly what Task Statement 4.4 is about.

**Retry-with-error-feedback.** When validation fails, re-prompting helps *only if
you tell the model what was wrong*. The effective follow-up request includes
three things: the original document, the failed extraction, and the **specific**
validation errors. "Please try again" wastes a call.

**The limits of retry.** Retrying is worthwhile for some error classes and
useless for others:

| Error kind | Example | Retry? |
|---|---|---|
| `format` | date as `06/01/2026` instead of ISO `2026-06-01`; currency casing | **yes** |
| `structural` | required field omitted, but the value IS in the document | **yes** |
| `info_absent` | required field's value is simply not in the source document | **no** |
| `source_conflict` | stated total genuinely ≠ sum of line items; contradictory dates | **no** |

The last two never improve on retry: the model cannot invent information that
isn't there, nor reconcile numbers the *source* got wrong. Looping on them just
burns tokens and latency — detect them and stop.

**Semantic vs syntax, self-correction fields.** The self-correction pattern from
the guide: extract `calculated_total` alongside `stated_total` and compare them;
add a `conflict_detected` boolean for internally-inconsistent source data; and
attach a `detected_pattern` label (e.g. `"stated_total_mismatch"`) to each
finding so you can later analyse how often each pattern is a true problem versus a
false positive that developers dismiss.

## Tasks

You will complete two modules in `starter/` (public API must match `solution/`).

### 1. `starter/models.py` — the semantic validator

The fields are provided. Implement the `_reconcile` `model_validator(mode="after")`:

- compute `calculated_total = round(sum(item.amount for item in line_items), 2)`
  and assign it to `self.calculated_total`;
- if `abs(calculated_total - stated_total) > TOTAL_TOLERANCE`: set
  `conflict_detected=True`, `detected_pattern="stated_total_mismatch"`, and
  **raise `ValueError`** whose message names *both* totals and the pattern label;
- if `due_date` is set and precedes `invoice_date`: set the flags with
  `detected_pattern="due_date_before_invoice_date"` and raise `ValueError`;
- otherwise return `self`.

### 2. `starter/retry.py` — the retry/feedback loop

- `is_retryable_error(kind) -> bool` — `format`/`structural` → `True`;
  `info_absent`/`source_conflict` → `False`; unknown kind → `ValueError`.
- `classify_error(error, document="") -> str` — map a `ValidationError` (or one
  of its sub-errors) to a kind. A "missing" field is `info_absent` when no
  `FIELD_HINTS` word for it appears in the document, else `structural`. A
  mismatch/contradiction message is `source_conflict`. Otherwise `format`.
- `should_retry(document, error) -> bool` — `False` as soon as any sub-error is
  non-retryable.
- `build_extraction_tool() -> dict` — the extraction tool (its `input_schema` is
  the output shape).
- `extract_with_retry(client, document, *, max_retries=2) -> dict` — call the
  client forcing the tool, validate with `InvoiceExtraction`, and on failure
  append the **specific** errors (with the failed extraction and original
  document) to the next request and retry. Stop early when `should_retry` is
  `False`. Return `{"data": ..., "attempts": int, "succeeded": bool}` (plus
  `"error"` / `"detected_pattern"` on failure). `max_retries` counts retries
  *after* the first attempt.

Inject the client (never construct `anthropic.Anthropic()` inside these
functions) so the tests run offline against `MockAnthropic`.

## Deliverables

- Completed `starter/models.py` and `starter/retry.py` with the same public API
  as `solution/`.
- All deterministic tests in `tests/test_lab10.py` passing.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-10-validation-retry
```

Against the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-10-validation-retry -q
```

## Stretch goals

1. **Attempt log.** Return a per-attempt trail (kind, `detected_pattern`, whether
   a retry was issued) so you can aggregate false-positive rates by pattern.
2. **Escalation hook.** When `should_retry` is `False`, route the document to a
   `needs_human_review` queue instead of silently returning `succeeded=False`.
3. **Distinguish extraction error from source error.** A sum mismatch *might* be
   the model misreading a line item (retryable) rather than a bad source total.
   Add a bounded retry that re-checks line items once before classifying the
   mismatch as a `source_conflict`.
4. **Tolerance policy.** Make `TOTAL_TOLERANCE` currency-aware (e.g. 0 for JPY,
   0.01 for USD) and explain why a fixed float tolerance is safer than `==`.
