"""Human-review routing and confidence calibration (Lab 18 — REFERENCE SOLUTION).

Public API (must match starter/):

    route_for_review(extraction: dict, threshold: float) -> str
    calibrate_threshold(validation_set: list[dict], target_precision: float) -> float
    stratified_sample(extractions: list[dict], strata_key: str,
                      per_stratum: int, rng_seed: int) -> list
    accuracy_by_segment(labeled: list[dict], segment_key: str) -> dict

Data model
----------
An *extraction* is a plain dict with at least:

    {
      "doc_type": "invoice",
      "confidences": {"vendor": 0.99, "total": 0.95, ...},  # field-level scores
      "ambiguous": False,        # optional flag
      "contradictory": False,    # optional flag
      "correct": True,           # ground-truth label (validation/labeled sets only)
    }

The single scalar confidence for an extraction is the **weakest field**
(``min`` of the field-level scores): a record is only as trustworthy as its
least-confident field. Everything downstream keys off that.
"""

from __future__ import annotations

import random
from typing import Any

__all__ = [
    "overall_confidence",
    "route_for_review",
    "calibrate_threshold",
    "stratified_sample",
    "accuracy_by_segment",
]


def overall_confidence(extraction: dict[str, Any]) -> float | None:
    """The extraction's scalar confidence = the minimum field-level score.

    Returns ``None`` when no field confidences are present (treated as unknown,
    which the router sends to a human).
    """
    confs = extraction.get("confidences") or {}
    if not confs:
        return None
    return min(confs.values())


def route_for_review(extraction: dict[str, Any], threshold: float) -> str:
    """Return ``"auto"`` to accept the extraction or ``"human"`` to escalate.

    Escalate to a human when EITHER:
      * the source document is flagged ``ambiguous`` or ``contradictory`` (no
        confidence score can rescue a contradictory source), OR
      * the extraction's weakest-field confidence is below ``threshold`` (or
        absent).

    Otherwise auto-accept. This prioritizes scarce reviewer capacity on the
    records most likely to be wrong.
    """
    if extraction.get("ambiguous") or extraction.get("contradictory"):
        return "human"
    conf = overall_confidence(extraction)
    if conf is None:
        return "human"
    return "auto" if conf >= threshold else "human"


def calibrate_threshold(
    validation_set: list[dict[str, Any]],
    target_precision: float,
) -> float:
    """Choose the lowest confidence threshold whose auto-accepted precision
    meets ``target_precision`` on a labeled ``validation_set``.

    "Precision" here = fraction of auto-accepted records that are actually
    ``correct``. A lower threshold auto-accepts more records (more automation)
    but usually at lower precision, so we want the **lowest** threshold that
    still clears the target — subject to that precision holding for every
    higher threshold too (robust to non-monotonic dips).

    Algorithm: scan candidate thresholds (the distinct observed confidences)
    from high to low; keep lowering the chosen threshold while the auto-accept
    precision stays at/above target; stop at the first candidate that drops
    below it. Returns ``1.0`` when no threshold meets the target (route
    everything to a human).
    """
    candidates = sorted(
        {
            c
            for e in validation_set
            if (c := overall_confidence(e)) is not None
        },
        reverse=True,
    )
    chosen = 1.0
    for t in candidates:
        auto = [e for e in validation_set if route_for_review(e, t) == "auto"]
        if not auto:
            continue
        precision = sum(1 for e in auto if e.get("correct")) / len(auto)
        if precision >= target_precision:
            chosen = t
        else:
            break
    return chosen


def stratified_sample(
    extractions: list[dict[str, Any]],
    strata_key: str,
    per_stratum: int,
    rng_seed: int,
) -> list[dict[str, Any]]:
    """Deterministically draw up to ``per_stratum`` records from EACH stratum.

    Strata are the distinct values of ``extractions[i][strata_key]`` (e.g.
    ``doc_type``). Sampling per stratum — rather than uniformly over the whole
    pool — guarantees every document type is represented even if it is a small
    slice of the corpus, which is exactly what surfaces a masked, low-accuracy
    segment during ongoing error-rate monitoring.

    The draw uses a seeded ``random.Random(rng_seed)`` and iterates strata in
    sorted order, so the same inputs + seed always yield the identical sample.
    Strata with fewer than ``per_stratum`` records contribute all of theirs.
    """
    groups: dict[Any, list[dict[str, Any]]] = {}
    for e in extractions:
        groups.setdefault(e[strata_key], []).append(e)

    rng = random.Random(rng_seed)
    sample: list[dict[str, Any]] = []
    for key in sorted(groups):
        items = groups[key]
        k = min(per_stratum, len(items))
        sample.extend(rng.sample(items, k))
    return sample


def accuracy_by_segment(
    labeled: list[dict[str, Any]],
    segment_key: str,
) -> dict[Any, float]:
    """Per-segment accuracy so a masked poor segment becomes visible.

    Groups ``labeled`` records by ``labeled[i][segment_key]`` and returns
    ``{segment: fraction_correct}``. An aggregate accuracy of 97% can hide a
    segment sitting at 70%; this breakdown is how you catch it before
    automating high-confidence extractions for that segment.
    """
    totals: dict[Any, list[int]] = {}
    for e in labeled:
        bucket = totals.setdefault(e[segment_key], [0, 0])
        bucket[0] += 1 if e.get("correct") else 0
        bucket[1] += 1
    return {seg: correct / n for seg, (correct, n) in totals.items()}
