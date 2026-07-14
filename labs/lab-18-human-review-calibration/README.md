# Lab 18 — Human Review & Confidence Calibration

| | |
|---|---|
| **Exam mapping** | Task Statement 5.5 |
| **Difficulty** | 6 / 10 |
| **Estimated time** | 2:00 |
| **Prerequisites** | L04 (structured output), L10 |

## Objective

Build the decision layer that sits between an extraction pipeline and full
automation: route the risky records to a human, calibrate the confidence
threshold on labeled data, and audit accuracy in a way that a single headline
number cannot fool. By the end you can:

- **Route** an extraction to `"auto"` or `"human"` from field-level confidence
  scores plus ambiguity/contradiction flags.
- **Calibrate** a confidence threshold against a labeled validation set to hit a
  target precision — instead of guessing "0.9 looks good."
- **Sample** high-confidence extractions with *stratified* random sampling so
  every document type is monitored, not just the common ones.
- **Segment** accuracy by document type so a masked, poorly-performing segment
  becomes visible despite a high aggregate.

## Background

A pipeline that reports **97% overall accuracy** sounds ready to automate. But
an aggregate is a weighted average, and a weighted average hides its worst
components. If invoices and receipts are 100% but handwritten notes are 70%, and
handwritten notes are only 10% of the corpus, you still see ~97% overall — and
you would happily automate a segment that is wrong nearly a third of the time.

Task Statement 5.5 is about not getting fooled by that number:

- **Field-level confidence, calibrated on labeled data.** A model can emit a
  confidence per field. Those scores are only useful once you have *calibrated* a
  threshold against a labeled validation set — chosen so the records you
  auto-accept actually hit your target precision. An extraction is only as
  trustworthy as its **weakest field**, so we score it by the `min`.
- **Route low-confidence or contradictory documents to human review.** Confidence
  below the threshold *or* an ambiguous/contradictory source means escalate.
  A contradictory source can't be rescued by a high confidence score. This
  prioritizes limited reviewer capacity on the records most likely to be wrong.
- **Stratified sampling for ongoing monitoring.** Even after you automate, you
  keep sampling *high-confidence* extractions to measure the real error rate and
  catch novel error patterns (including miscalibration — wrong answers with high
  confidence). Sampling *per stratum* guarantees small document types are still
  watched instead of being drowned out by the common ones.
- **Validate accuracy by segment before automating.** Break accuracy down by
  document type (and field) and confirm every segment clears the bar. Automate
  the segments that are consistently good; keep humans on the ones that aren't.

The provided `validation_set.json` is engineered exactly this way: **97%
aggregate**, with `handwritten_note` sitting at **70%**, and two of its wrong
extractions carrying deliberately *high* confidence (miscalibration) so you can
feel why sampling and segmentation — not the headline number — are what protect
you.

## Tasks

Complete the four functions in `starter/calibration.py` (same public API as
`solution/`). The `overall_confidence` helper is provided.

1. **`route_for_review(extraction, threshold) -> str`** — return `"human"` when
   the source is flagged `ambiguous`/`contradictory` **or** the weakest-field
   confidence is below `threshold` (or absent); otherwise `"auto"`.

2. **`calibrate_threshold(validation_set, target_precision) -> float`** — pick
   the **lowest** confidence threshold whose auto-accepted precision (fraction of
   auto-accepted records that are `correct`) meets `target_precision`. Scan the
   observed confidences high→low, keep lowering while precision holds, stop at the
   first drop. Return `1.0` when nothing meets the target.

3. **`stratified_sample(extractions, strata_key, per_stratum, rng_seed) -> list`**
   — draw up to `per_stratum` records from **each** stratum (distinct values of
   `strata_key`). Use a **seeded** `random.Random(rng_seed)` and a stable stratum
   order so the same inputs + seed always produce the identical sample.

4. **`accuracy_by_segment(labeled, segment_key) -> dict`** — return
   `{segment: fraction_correct}` grouped by `segment_key`, so the poor segment is
   visible next to the good ones.

An extraction dict looks like:

```json
{
  "doc_type": "invoice",
  "confidences": {"vendor": 0.99, "total": 0.95, "invoice_date": 0.97},
  "ambiguous": false,
  "contradictory": false,
  "correct": true
}
```

(`correct` is the ground-truth label; it is present in the validation/labeled
sets, not on live extractions you are routing.)

You can regenerate the data set with `uv run make_validation_set.py`
(`--stats-only` prints the accuracy breakdown; `--help` for all flags).

## Deliverables

- Completed `starter/calibration.py` with the same public API as `solution/`.
- All deterministic tests in `tests/test_lab18.py` passing.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-18-human-review-calibration
```

Compare against the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-18-human-review-calibration -q
```

## Stretch Goals

1. **Field-level segmentation.** Extend `accuracy_by_segment` (or add a sibling)
   to report accuracy per *field* as well as per document type — a field can be
   the masked weak spot even when every document type looks fine.
2. **Reviewer budget.** Given a fixed human-review capacity `N`, rank the
   `"human"`-routed records by ascending confidence and return the top `N` so the
   scarcest reviewers see the riskiest documents first.
3. **Calibration drift alarm.** Using a fresh stratified sample's labels,
   recompute segment accuracy and flag any segment that has dropped more than X
   points since calibration — the ongoing-monitoring loop closing on itself.
4. **Coverage vs. precision curve.** Sweep `target_precision` and plot the
   automation coverage (fraction auto-accepted) it buys, to choose an operating
   point deliberately.
