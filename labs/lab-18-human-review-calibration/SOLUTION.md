# Lab 18 — Solution notes

## Approach

Four small, pure functions form a review/automation decision layer over an
extraction pipeline (Task Statement 5.5). They share one idea: **an extraction
is only as trustworthy as its weakest field**, so the scalar confidence for a
record is the `min` of its field-level scores (`overall_confidence`).

- `route_for_review` — the per-record gate: flags first, then confidence.
- `calibrate_threshold` — chooses the gate's threshold from labeled data.
- `stratified_sample` — the ongoing-monitoring sampler.
- `accuracy_by_segment` — the audit that unmasks a weak segment.

All logic is deterministic and offline; the only randomness is a **seeded** RNG
inside `stratified_sample`.

## Key decisions & why

- **Why aggregate metrics mislead.** A headline accuracy is a weighted average
  over segments. A small segment can be terrible while the average stays high:
  the fixture is 97% overall but `handwritten_note` is 70% (10 of 100 records).
  Automating on the strength of "97%" ships a segment that is wrong ~30% of the
  time. `accuracy_by_segment` exists precisely to break the average back apart so
  that segment is impossible to miss. **Validate accuracy by segment before
  automating** — never on the aggregate alone.

- **Weakest-field scoring, not average.** Averaging confidences lets one very
  confident field paper over a shaky one. Taking the `min` means a single
  low-confidence field escalates the whole record — the safe default for
  extraction where any wrong field can be costly.

- **Flags beat confidence.** A `contradictory` or `ambiguous` source is routed to
  a human *regardless* of confidence. High confidence on a self-contradictory
  document is not reassurance; it's a reason to worry. Flags are checked first.

- **Calibration instead of a guessed threshold.** "0.9 looks reasonable" is not
  calibration. `calibrate_threshold` walks the *observed* confidences on a
  **labeled** validation set and picks the lowest threshold whose auto-accepted
  precision still meets the target. Lower threshold = more automation (coverage),
  usually at lower precision — so we want the lowest one that still clears the
  bar. Scanning high→low and stopping at the first dip makes the choice robust to
  a non-monotonic precision curve, and returning `1.0` (route everything to a
  human) is the honest answer when no threshold is good enough.

- **Stratified, seeded sampling for monitoring.** After automating, you keep
  sampling *high-confidence* extractions to measure the true error rate and catch
  novel patterns — including miscalibration (wrong-but-confident). Sampling
  uniformly over the pool would under-sample rare document types; **per-stratum**
  sampling guarantees each type is watched. Seeding (`random.Random(rng_seed)`)
  plus a sorted stratum order makes the audit reproducible and testable — no
  `Date.now()` / unseeded `random` surprises.

## Reference walkthrough

1. `overall_confidence(e)` → `min(e["confidences"].values())`, or `None` if
   empty.
2. `route_for_review(e, t)` → `"human"` if `e.get("ambiguous")` or
   `e.get("contradictory")`, or if confidence is `None` or `< t`; else `"auto"`.
3. `calibrate_threshold(vs, target)`:
   - candidates = distinct `overall_confidence` values, sorted descending;
   - for each `t`, `auto = [e for e in vs if route_for_review(e, t) == "auto"]`;
     skip empty; `precision = correct / len(auto)`;
   - while `precision >= target`, lower `chosen = t`; on the first `t` below
     target, `break`;
   - return `chosen` (defaults to `1.0`).
4. `stratified_sample(items, key, per, seed)` → group by `items[i][key]`; with
   `rng = random.Random(seed)`, iterate `sorted(groups)` and
   `rng.sample(group, min(per, len(group)))`; concatenate.
5. `accuracy_by_segment(labeled, key)` → group by `labeled[i][key]`, return
   `{segment: correct / total}`.

On the fixture, `calibrate_threshold(vs, 0.98)` returns ~0.928: raising the
target from 0.97 to 0.98 pushes the threshold up past the two miscalibrated
handwritten errors — a concrete demonstration of precision-vs-coverage.

## Common mistakes

- **Trusting the aggregate.** Reporting 97% and automating everything. Always
  segment first; the fixture is built to punish this.
- **Averaging field confidences.** Use the `min`; an average hides the weak field.
- **Letting confidence override a contradictory source.** Check flags before
  confidence; a confident answer to a contradictory document is still suspect.
- **Guessing the threshold.** Calibrate it on labeled data against a target
  precision instead of hard-coding `0.9`.
- **Choosing the highest passing threshold.** You want the *lowest* threshold
  that still meets the target, to maximize automation coverage.
- **Unseeded sampling.** Using bare `random.random()` / `random.sample()` without
  a seed makes the monitoring un-reproducible and the tests flaky. Seed it.
- **Uniform (non-stratified) sampling.** Rare document types get under-sampled
  and their errors stay masked — the whole point of stratifying.

## Checklist

- [ ] `route_for_review` escalates on flags and on weakest-field confidence
      `< threshold` (and on missing confidences); auto-accepts otherwise.
- [ ] `calibrate_threshold` returns the lowest threshold meeting the target and
      `1.0` when none does; result satisfies the target on the labeled set.
- [ ] `stratified_sample` is reproducible for a fixed seed, covers every stratum,
      and takes `min(per_stratum, stratum_size)` from each.
- [ ] `accuracy_by_segment` returns per-segment fractions and reveals the poor
      `handwritten_note` segment despite the ~97% aggregate.
- [ ] `LAB_TARGET=solution uv run pytest lab-18-human-review-calibration -q` is
      green.
