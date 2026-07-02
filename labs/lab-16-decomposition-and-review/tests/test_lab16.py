"""Deterministic tests for L16 — Task Decomposition & Multi-pass Review.

Runs against starter/ by default (learner's work, expected to fail with
NotImplementedError) and solution/ when LAB_TARGET=solution (must be green).
All tests are offline: the one Claude-driven test uses MockAnthropic.
"""

from __future__ import annotations

import pytest

from labkit import lab_module
from mock_anthropic import MockAnthropic, tool_use_response

dc = lab_module(__file__, "decomposition")


# The 14-file stock-tracking PR from Sample Question 12 (see review_scenario.md).
PR_FILES = [
    "inventory.py",
    "stock_levels.py",
    "reorder.py",
    "warehouse.py",
    "sku_catalog.py",
    "transfers.py",
    "suppliers.py",
    "purchase_orders.py",
    "stock_events.py",
    "valuation.py",
    "api/stock_routes.py",
    "api/schemas.py",
    "db/models.py",
    "tests/test_stock.py",
]


# --------------------------------------------------------------------------- #
# choose_decomposition (Task Statement 1.6)
# --------------------------------------------------------------------------- #
def test_predictable_review_uses_prompt_chaining() -> None:
    task = {
        "type": "multi_file_review",
        "goal": (
            "Review the 14-file stock-tracking PR: analyze each file for local "
            "bugs, then run a cross-file integration pass."
        ),
        "files": PR_FILES,
    }
    assert dc.choose_decomposition(task) == "prompt_chaining"


def test_legacy_test_task_uses_dynamic() -> None:
    task = {
        "type": "add_tests",
        "goal": (
            "Add comprehensive tests to a legacy codebase with no existing test "
            "suite; map the structure and adapt as dependencies are discovered."
        ),
    }
    assert dc.choose_decomposition(task) == "dynamic"


def test_explicit_open_ended_flag_overrides() -> None:
    assert dc.choose_decomposition({"open_ended": True}) == "dynamic"
    assert dc.choose_decomposition({"open_ended": False}) == "prompt_chaining"


# --------------------------------------------------------------------------- #
# plan_review_passes (Task Statements 1.6 + 4.6)
# --------------------------------------------------------------------------- #
def test_plan_yields_one_local_pass_per_file_plus_one_integration() -> None:
    passes = dc.plan_review_passes(PR_FILES)
    assert len(passes) == len(PR_FILES) + 1  # 14 local + 1 integration == 15

    local = [p for p in passes if p["kind"] == "local"]
    integration = [p for p in passes if p["kind"] == "integration"]
    assert len(local) == 14
    assert len(integration) == 1  # EXACTLY one integration pass

    # Each local pass covers exactly one distinct file, in order.
    assert [p["file"] for p in local] == PR_FILES
    for p in local:
        assert p["files"] == [p["file"]]

    # The integration pass is last and spans every file (cross-file scope).
    last = passes[-1]
    assert last["kind"] == "integration"
    assert last["scope"] == "cross_file"
    assert set(last["files"]) == set(PR_FILES)


def test_plan_rejects_empty_file_list() -> None:
    with pytest.raises(ValueError):
        dc.plan_review_passes([])


# --------------------------------------------------------------------------- #
# is_independent_review (Task Statement 4.6)
# --------------------------------------------------------------------------- #
def test_self_review_is_not_independent() -> None:
    # Same session id == the generator reviewing its own work.
    assert dc.is_independent_review(
        {"generator_session_id": "sess-1", "reviewer_session_id": "sess-1"}
    ) is False
    # Explicit shared-context flag.
    assert dc.is_independent_review({"shares_reasoning_context": True}) is False
    # A fresh session that was still handed the generation reasoning trace.
    assert dc.is_independent_review(
        {
            "generator_session_id": "gen",
            "reviewer_session_id": "rev",
            "includes_generation_reasoning": True,
            "shares_reasoning_context": True,
        }
    ) is False


def test_fresh_instance_is_independent() -> None:
    assert dc.is_independent_review(
        {"generator_session_id": "gen", "reviewer_session_id": "rev"}
    ) is True
    assert dc.is_independent_review({"shares_reasoning_context": False}) is True


# --------------------------------------------------------------------------- #
# route_by_confidence (Task Statements 4.6 + 5.5)
# --------------------------------------------------------------------------- #
def test_route_partitions_by_threshold() -> None:
    findings = [
        {"issue": "off-by-one", "confidence": 0.95},
        {"issue": "unused import", "confidence": 0.80},  # exactly at threshold
        {"issue": "maybe a race", "confidence": 0.40},
        {"issue": "no confidence reported"},  # missing -> human review
    ]
    routed = dc.route_by_confidence(findings, threshold=0.80)

    auto_issues = {f["issue"] for f in routed["auto"]}
    human_issues = {f["issue"] for f in routed["human_review"]}
    assert auto_issues == {"off-by-one", "unused import"}
    assert human_issues == {"maybe a race", "no confidence reported"}

    # Partition is total and non-overlapping.
    assert len(routed["auto"]) + len(routed["human_review"]) == len(findings)


# --------------------------------------------------------------------------- #
# Optional: an independent second instance catches a finding the generator
# missed (MockAnthropic, deterministic).
# --------------------------------------------------------------------------- #
def test_independent_instance_catches_missed_finding() -> None:
    # A fresh instance (no generator context) surfaces a bug the generator,
    # attached to its own reasoning, would not have questioned.
    client = MockAnthropic(
        responses=[
            tool_use_response(
                "report_finding",
                {
                    "file": "reorder.py",
                    "line": 42,
                    "issue": "Off-by-one in restock threshold: uses < instead of <=",
                    "severity": "high",
                    "confidence": 0.9,
                },
            )
        ]
    )

    findings = dc.independent_second_pass(
        client, {"file": "reorder.py", "code": "if level < threshold: reorder()"}
    )
    assert findings, "the independent reviewer should return at least one finding"
    assert findings[0]["issue"].startswith("Off-by-one")

    # This reviewer is independent, unlike a same-session self-review.
    assert dc.is_independent_review(
        {"generator_session_id": "gen", "reviewer_session_id": "rev"}
    ) is True

    # The high-confidence finding routes to auto; low-confidence would not.
    routed = dc.route_by_confidence(findings, threshold=0.8)
    assert findings[0] in routed["auto"]

    # The review was forced to emit structured findings, not prose.
    assert client.calls[0]["tool_choice"] == {"type": "any"}
