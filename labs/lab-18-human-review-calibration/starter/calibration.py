"""Human-review routing and confidence calibration (Lab 18 — STARTER).

Implement the four public functions below. Keep the SAME public API as
``solution/calibration.py`` so the shared test suite runs against both.

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

Treat the extraction's scalar confidence as the **weakest field** — the ``min``
of its field-level scores. A record is only as trustworthy as its least
confident field. The provided ``overall_confidence`` helper does this for you.
"""

from __future__ import annotations

import random  # noqa: F401  (needed for a SEEDED rng in stratified_sample)
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

    Returns ``None`` when no field confidences are present. (Already
    implemented — use it in the functions below.)
    """
    confs = extraction.get("confidences") or {}
    if not confs:
        return None
    return min(confs.values())


def route_for_review(extraction: dict[str, Any], threshold: float) -> str:
    """Return ``"auto"`` (accept) or ``"human"`` (escalate).

    Escalate to a human when EITHER the source is flagged ``ambiguous`` or
    ``contradictory``, OR the weakest-field confidence is below ``threshold``
    (or absent). Otherwise auto-accept.
    """
    # TODO: implement per the docstring (check flags first, then confidence).
    raise NotImplementedError("route_for_review: return 'auto' or 'human'")


def calibrate_threshold(
    validation_set: list[dict[str, Any]],
    target_precision: float,
) -> float:
    """Return the lowest confidence threshold whose auto-accepted precision
    meets ``target_precision`` on the labeled ``validation_set``.

    Precision = fraction of auto-accepted records that are ``correct``. Scan the
    distinct observed confidences from high to low; keep lowering the chosen
    threshold while precision stays >= target; stop at the first drop below it.
    Return ``1.0`` when nothing meets the target.
    """
    # TODO: implement per the docstring. Use route_for_review to decide which
    # records are auto-accepted at a candidate threshold.
    raise NotImplementedError("calibrate_threshold: pick a threshold from the labeled set")


def stratified_sample(
    extractions: list[dict[str, Any]],
    strata_key: str,
    per_stratum: int,
    rng_seed: int,
) -> list[dict[str, Any]]:
    """Deterministically draw up to ``per_stratum`` records from EACH stratum
    (distinct values of ``extractions[i][strata_key]``).

    Use a SEEDED ``random.Random(rng_seed)`` and iterate strata in sorted order
    so the same inputs + seed always yield the identical sample. Strata smaller
    than ``per_stratum`` contribute all of their records.
    """
    # TODO: group by strata_key, then seeded-sample min(per_stratum, len) each.
    raise NotImplementedError("stratified_sample: deterministic per-stratum sample")


def accuracy_by_segment(
    labeled: list[dict[str, Any]],
    segment_key: str,
) -> dict[Any, float]:
    """Return ``{segment: fraction_correct}`` grouped by ``labeled[i][segment_key]``.

    This breakdown is what reveals a poor segment that a high aggregate hides.
    """
    # TODO: group by segment_key and compute per-segment accuracy.
    raise NotImplementedError("accuracy_by_segment: per-segment accuracy dict")
