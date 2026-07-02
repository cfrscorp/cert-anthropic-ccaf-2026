"""Deterministic tests for Lab 18 — Human Review & Confidence Calibration.

Run the learner's work (default):   uv run pytest lab-18-human-review-calibration -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-18-human-review-calibration -q
"""

from __future__ import annotations

import json

import pytest
from labkit import lab_module, lab_root

mod = lab_module(__file__, "calibration")


# --------------------------------------------------------------------------- #
# Fixtures / helpers                                                          #
# --------------------------------------------------------------------------- #
def _validation_set() -> list[dict]:
    path = lab_root(__file__) / "validation_set.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _clean(conf: float, doc_type: str = "invoice") -> dict:
    """A flag-free extraction whose every field has confidence ``conf``."""
    return {
        "doc_type": doc_type,
        "confidences": {"a": conf, "b": conf, "c": conf},
        "ambiguous": False,
        "contradictory": False,
    }


def _precision_of_auto(validation_set: list[dict], threshold: float) -> tuple[int, float]:
    auto = [e for e in validation_set if mod.route_for_review(e, threshold) == "auto"]
    if not auto:
        return 0, 0.0
    return len(auto), sum(1 for e in auto if e["correct"]) / len(auto)


# --------------------------------------------------------------------------- #
# route_for_review                                                            #
# --------------------------------------------------------------------------- #
def test_route_high_confidence_clean_is_auto():
    assert mod.route_for_review(_clean(0.98), threshold=0.90) == "auto"


def test_route_low_confidence_is_human():
    # Weakest field (0.40) is below threshold -> escalate.
    ext = {"confidences": {"a": 0.99, "b": 0.40}, "ambiguous": False, "contradictory": False}
    assert mod.route_for_review(ext, threshold=0.90) == "human"


def test_route_contradictory_source_is_human_despite_high_confidence():
    ext = {"confidences": {"a": 0.99, "b": 0.99}, "contradictory": True}
    assert mod.route_for_review(ext, threshold=0.90) == "human"


def test_route_ambiguous_source_is_human_despite_high_confidence():
    ext = {"confidences": {"a": 0.99, "b": 0.99}, "ambiguous": True}
    assert mod.route_for_review(ext, threshold=0.90) == "human"


def test_route_missing_confidences_is_human():
    assert mod.route_for_review({"confidences": {}}, threshold=0.10) == "human"


def test_route_uses_weakest_field_not_average():
    # Average is 0.80 (would pass), but the weakest field is 0.60 (must fail).
    ext = {"confidences": {"a": 1.0, "b": 0.60}}
    assert mod.route_for_review(ext, threshold=0.70) == "human"


# --------------------------------------------------------------------------- #
# calibrate_threshold                                                         #
# --------------------------------------------------------------------------- #
def test_calibrate_returns_threshold_meeting_target():
    vs = _validation_set()
    target = 0.98
    t = mod.calibrate_threshold(vs, target_precision=target)
    assert 0.0 < t <= 1.0
    n, precision = _precision_of_auto(vs, t)
    assert n > 0, "calibrated threshold should still auto-accept some records"
    assert precision >= target, f"precision {precision:.4f} below target {target}"


def test_calibrate_stricter_target_needs_higher_threshold():
    vs = _validation_set()
    lenient = mod.calibrate_threshold(vs, target_precision=0.97)
    strict = mod.calibrate_threshold(vs, target_precision=0.99)
    assert strict >= lenient


def test_calibrate_impossible_target_routes_everything_to_human():
    # No auto-accept set can reach 100% precision because a wrong extraction is
    # perfectly confident (miscalibration). Expect the fall-back threshold.
    vs = [
        {"confidences": {"a": 1.0}, "correct": False},
        {"confidences": {"a": 0.95}, "correct": True},
    ]
    t = mod.calibrate_threshold(vs, target_precision=1.0)
    assert t == 1.0


# --------------------------------------------------------------------------- #
# stratified_sample                                                           #
# --------------------------------------------------------------------------- #
def test_stratified_sample_is_reproducible_with_fixed_seed():
    vs = _validation_set()
    a = mod.stratified_sample(vs, "doc_type", per_stratum=3, rng_seed=42)
    b = mod.stratified_sample(vs, "doc_type", per_stratum=3, rng_seed=42)
    assert [e["doc_id"] for e in a] == [e["doc_id"] for e in b]


def test_stratified_sample_covers_every_stratum():
    vs = _validation_set()
    all_types = {e["doc_type"] for e in vs}
    sample = mod.stratified_sample(vs, "doc_type", per_stratum=3, rng_seed=42)
    assert {e["doc_type"] for e in sample} == all_types


def test_stratified_sample_respects_per_stratum_count():
    vs = _validation_set()
    per = 4
    sample = mod.stratified_sample(vs, "doc_type", per_stratum=per, rng_seed=7)
    counts: dict[str, int] = {}
    sizes: dict[str, int] = {}
    for e in vs:
        sizes[e["doc_type"]] = sizes.get(e["doc_type"], 0) + 1
    for e in sample:
        counts[e["doc_type"]] = counts.get(e["doc_type"], 0) + 1
    for dtype, n in counts.items():
        assert n == min(per, sizes[dtype])


def test_stratified_sample_different_seed_can_differ():
    vs = _validation_set()
    a = mod.stratified_sample(vs, "doc_type", per_stratum=3, rng_seed=1)
    b = mod.stratified_sample(vs, "doc_type", per_stratum=3, rng_seed=999)
    # Not guaranteed for tiny strata, but across the full corpus the picks differ.
    assert [e["doc_id"] for e in a] != [e["doc_id"] for e in b]


# --------------------------------------------------------------------------- #
# accuracy_by_segment                                                         #
# --------------------------------------------------------------------------- #
def test_accuracy_by_segment_reveals_masked_poor_segment():
    vs = _validation_set()
    seg = mod.accuracy_by_segment(vs, "doc_type")

    aggregate = sum(1 for e in vs if e["correct"]) / len(vs)
    assert aggregate >= 0.95, "fixture should have a high aggregate accuracy"

    assert "handwritten_note" in seg
    worst = min(seg.values())
    # The poor segment is well below both the aggregate and the best segment.
    assert worst < 0.80
    assert seg["handwritten_note"] == worst
    assert seg["handwritten_note"] < aggregate - 0.15


def test_accuracy_by_segment_values_are_fractions():
    vs = _validation_set()
    seg = mod.accuracy_by_segment(vs, "doc_type")
    assert all(0.0 <= v <= 1.0 for v in seg.values())
