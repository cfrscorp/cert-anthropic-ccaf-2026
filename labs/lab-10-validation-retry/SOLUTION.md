# Lab 10 — Solution notes

## Approach

Two modules, one loop:

1. **`models.py`** validates *meaning*. Pydantic types already enforce the schema
   (shape, types, required fields); the `model_validator(mode="after")` adds the
   semantic checks a schema cannot express — the `calculated_total` vs
   `stated_total` reconciliation and a date-order check. Failures raise
   `ValueError` (which Pydantic surfaces as `ValidationError`) with a message that
   names the specific discrepancy and a `detected_pattern` label.

2. **`retry.py`** runs extract → validate → (maybe) retry. On a validation
   failure it first asks `should_retry`: if the failure is `info_absent` or
   `source_conflict` it stops immediately; otherwise it appends the *specific*
   error text (with the failed extraction and the original document) to the next
   request and loops up to `max_retries` more times.

## Key decisions & why

### When retry helps vs is futile

The whole point of Task Statement 4.4 is that retry is not free and not always
useful. We encode four kinds:

- **`format`** (retryable) — the info is present but shaped wrong: a date as
  `06/01/2026`, a mis-cased currency. Telling the model the exact rule it broke
  reliably fixes it.
- **`structural`** (retryable) — a required field was dropped, *but the value is
  in the document*. A pointed "you omitted X, it's in the header" recovers it.
- **`info_absent`** (not retryable) — the value is genuinely not in the source.
  No amount of re-prompting can conjure it; retrying only wastes calls. We detect
  this by checking `FIELD_HINTS`: if none of the words that *would* accompany the
  field appear in the document, the info is absent.
- **`source_conflict`** (not retryable) — the *source itself* is inconsistent:
  the stated total doesn't equal the line items, or the due date precedes the
  invoice date. The model cannot reconcile numbers that don't add up in the
  document. This is where `conflict_detected` is the right signal — flag it and
  escalate, don't loop.

`should_retry` returns `False` as soon as **any** sub-error is non-retryable,
because a single unfixable problem makes the whole retry pointless.

### Semantic vs syntax errors

Syntax errors (malformed JSON, missing keys, wrong types) are *eliminated by tool
use* — the API guarantees the tool `input` matches `input_schema`. So this lab
spends no effort re-checking JSON validity; it assumes the shape is right and
attacks meaning. The Pydantic types are a belt-and-suspenders backstop for the
raw-dict path, but in the tool-use flow they essentially never fire. The
interesting failures — totals that don't sum, a value in the wrong field,
contradictory dates — are *semantic*, and only a domain-aware validator catches
them.

### `detected_pattern` for false-positive analysis

Each finding carries a stable label (`stated_total_mismatch`,
`due_date_before_invoice_date`). Over many documents you can aggregate how often
each pattern turns out to be a real problem versus a false positive a reviewer
dismisses — the feedback-loop-design skill in the guide. The label travels in the
raised message and is surfaced on the failure result as `detected_pattern`.

### Feedback must be specific

`_format_feedback` renders each error as `- <field path>: <message>` and
`_build_messages` places it *after* the original document and the failed
extraction, exactly the three ingredients the guide calls for. A generic retry
prompt is the classic mistake — it rarely changes the model's output.

## Reference walkthrough

- `InvoiceExtraction._reconcile`: computes `calculated_total`, compares to
  `stated_total` within `TOTAL_TOLERANCE` (float money never use `==`), then
  checks date order. Sets `conflict_detected` + `detected_pattern` before raising.
- `is_retryable_error`: a dict lookup; unknown kinds raise `ValueError` so typos
  fail loudly rather than silently defaulting.
- `classify_error` / `_classify_single`: message-first (mismatch → conflict),
  then `missing` → `info_absent`/`structural` via `FIELD_HINTS`, else `format`.
  Non-retryable kinds win in the aggregate.
- `extract_with_retry`: `attempts` starts at 0 and increments per model call;
  `max_retries=2` means up to 3 calls. On `ValidationError` it consults
  `should_retry`, then either returns `succeeded=False` (with `error` and
  `detected_pattern`) or loops with feedback set.

## Common mistakes

- **Comparing floats with `==`.** `sum(...) == stated_total` fails on rounding
  noise. Use a tolerance (`abs(diff) > TOTAL_TOLERANCE`).
- **Retrying everything.** Looping on `info_absent` / `source_conflict` burns the
  budget and still fails. Check `should_retry` *before* re-calling.
- **Vague feedback.** Re-sending the same prompt (or "please fix it") without the
  specific errors rarely helps.
- **Dropping the document on retry.** Self-correction needs the original source,
  the failed extraction, *and* the errors — all three.
- **Counting attempts wrong.** `max_retries` is retries *after* the first attempt.
- **Setting fields after raising and expecting them to persist.** When the
  validator raises, the instance is discarded — that's why the specifics (and the
  pattern label) live in the *message*, not just on the object.

## Checklist

- [ ] `_reconcile` computes `calculated_total` and reconciles it with tolerance.
- [ ] Mismatch and date-conflict both set `detected_pattern` and raise with a
      specific message.
- [ ] `is_retryable_error` maps all four kinds and rejects unknown kinds.
- [ ] `should_retry` returns `False` for `info_absent` and `source_conflict`.
- [ ] `extract_with_retry` appends the specific errors + document on retry.
- [ ] It gives up (no extra calls) when a retry can't help.
- [ ] `LAB_TARGET=solution uv run pytest lab-10-validation-retry -q` is green;
      the default (starter) run fails.
