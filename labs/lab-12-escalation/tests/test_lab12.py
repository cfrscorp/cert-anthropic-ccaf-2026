"""Deterministic tests for L12 — Escalation & Ambiguity Resolution (Task 5.2).

These lock in the calibrated escalation contract:

  * ``decide`` returns the labeled action for every scenario in ``cases.json``.
  * ``decide`` never changes its answer based on sentiment or self-reported
    confidence (the unreliable proxies the guide warns against).
  * ``uses_unreliable_signal`` flags a policy that branches on sentiment/
    confidence and clears a criteria-based one.
  * ``build_escalation_criteria`` embeds the few-shot examples it is given.

Run from labs/:  uv run pytest lab-12-escalation
Validate ref:     LAB_TARGET=solution uv run pytest lab-12-escalation
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from labkit import lab_module, lab_root

esc = lab_module(__file__, "escalation")

CASES = json.loads((lab_root(__file__) / "cases.json").read_text())
VALID_DECISIONS = {"ESCALATE", "ASK_CLARIFY", "RESOLVE"}


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_decide_matches_labeled_cases(case):
    """decide() must return the labeled decision for each scenario."""
    result = esc.decide(case["context"])
    assert result in VALID_DECISIONS
    assert result == case["expected"], (
        f"{case['id']}: expected {case['expected']}, got {result} "
        f"({case.get('note', '')})"
    )


def test_decide_ignores_sentiment():
    """Flipping sentiment across the spectrum must not change any decision."""
    for case in CASES:
        base = esc.decide(case["context"])
        for mood in ("furious", "cheerful", "neutral", "desperate", None):
            variant = copy.deepcopy(case["context"])
            variant["sentiment"] = mood
            assert esc.decide(variant) == base, (
                f"{case['id']}: sentiment={mood!r} changed the decision "
                "(sentiment is an unreliable proxy and must be ignored)."
            )


def test_decide_ignores_self_reported_confidence():
    """Sweeping confidence from 0.0 to 1.0 must not change any decision."""
    for case in CASES:
        base = esc.decide(case["context"])
        for conf in (0.0, 0.2, 0.5, 0.8, 1.0):
            variant = copy.deepcopy(case["context"])
            variant["self_reported_confidence"] = conf
            assert esc.decide(variant) == base, (
                f"{case['id']}: confidence={conf} changed the decision "
                "(self-reported confidence is poorly calibrated; ignore it)."
            )


def test_explicit_human_request_escalates_without_investigation():
    """An explicit human request escalates even when everything else is routine."""
    ctx = {
        "explicit_human_request": True,
        "policy_status": "covered",
        "customer_matches": 1,
        "within_capability": True,
        "straightforward": True,
    }
    assert esc.decide(ctx) == "ESCALATE"


def test_multiple_matches_ask_clarify():
    """Multiple customer matches -> ASK_CLARIFY (request another identifier)."""
    ctx = {"customer_matches": 3, "policy_status": "covered"}
    assert esc.decide(ctx) == "ASK_CLARIFY"


def test_uses_unreliable_signal_flags_sentiment_confidence_policy():
    """A policy that branches on sentiment/confidence is flagged True."""
    sentiment_policy = {
        "name": "sentiment-threshold",
        "signals": ["sentiment_score", "self_reported_confidence"],
        "escalate_when": "sentiment_score > 0.7",
    }
    assert esc.uses_unreliable_signal(sentiment_policy) is True


def test_uses_unreliable_signal_clears_criteria_policy():
    """A criteria-based policy with no sentiment/confidence signals is False."""
    criteria_policy = {
        "name": "explicit-criteria",
        "signals": [
            "explicit_human_request",
            "policy_status",
            "customer_matches",
            "can_make_progress",
        ],
    }
    assert esc.uses_unreliable_signal(criteria_policy) is False


def test_build_escalation_criteria_embeds_examples():
    """The snippet must embed every example's situation and decision verbatim."""
    examples = [
        {
            "situation": "Customer says 'just give me a human'.",
            "decision": "ESCALATE",
            "reason": "Honor an explicit request immediately, not sentiment.",
        },
        {
            "situation": "Two accounts match 'J. Smith'.",
            "decision": "ASK_CLARIFY",
            "reason": "Request another identifier rather than guessing.",
        },
    ]
    snippet = esc.build_escalation_criteria(examples)
    assert isinstance(snippet, str)
    for example in examples:
        assert example["situation"] in snippet
        assert example["decision"] in snippet
        assert example["reason"] in snippet


def test_build_escalation_criteria_states_explicit_criteria():
    """The snippet should state explicit criteria, not defer to sentiment."""
    snippet = esc.build_escalation_criteria(
        [{"situation": "x", "decision": "RESOLVE"}]
    ).lower()
    assert "escalate" in snippet
    assert "ask_clarify" in snippet or "clarif" in snippet
    assert "resolve" in snippet


def test_build_escalation_criteria_rejects_empty():
    """Few-shot needs shots: empty examples raises ValueError."""
    with pytest.raises(ValueError):
        esc.build_escalation_criteria([])
