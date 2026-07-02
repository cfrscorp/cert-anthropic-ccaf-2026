"""Deterministic tests for L05 — Tool Interface Design & Disambiguation.

Runs against starter/ by default (learner's work) and solution/ when
LAB_TARGET=solution. The single @pytest.mark.llm test is excluded from the
default run and auto-skips without ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json

import pytest

from labkit import lab_module, lab_root, target_dir

td = lab_module(__file__, "tool_design")
ROOT = lab_root(__file__)
TARGET = target_dir(__file__)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
def _tools_before() -> dict[str, dict]:
    data = json.loads((ROOT / "tools_before.json").read_text())
    return {t["name"]: t for t in data}


def _tools_after() -> dict[str, dict]:
    data = json.loads((TARGET / "tools_after.json").read_text())
    return {t["name"]: t for t in data}


BEFORE = _tools_before()

# Elements every improved description must contain (checked case-insensitively).
_REQUIRED_MARKERS = ["input format", "example", "edge case"]


def _has_required_elements(description: str) -> None:
    low = description.lower()
    for marker in _REQUIRED_MARKERS:
        assert marker in low, f"description missing required element: {marker!r}"
    # Boundary clause: "Use this when ... not when ...".
    assert "use this when" in low, "description missing 'Use this when' boundary"
    assert "not when" in low, "description missing 'not when' boundary"


# --------------------------------------------------------------------------- #
# improve_description
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["get_customer", "lookup_order"])
def test_improved_description_has_required_elements(name: str) -> None:
    improved = td.improve_description(BEFORE[name])
    assert improved["name"] == name
    _has_required_elements(improved["description"])
    # It must actually be an improvement, not a passthrough of the minimal text.
    assert len(improved["description"]) > len(BEFORE[name]["description"]) * 3


def test_improved_similar_tools_differ_and_are_unambiguous() -> None:
    a = td.improve_description(BEFORE["get_customer"])
    b = td.improve_description(BEFORE["lookup_order"])
    assert a["description"] != b["description"]
    # After rewriting, the pair must no longer read as ambiguous.
    assert td.describes_ambiguously(a, b) is False


# --------------------------------------------------------------------------- #
# split_analyze_document
# --------------------------------------------------------------------------- #
def test_split_returns_three_named_tools() -> None:
    tools = td.split_analyze_document()
    assert isinstance(tools, list) and len(tools) == 3
    names = [t["name"] for t in tools]
    assert set(names) == {
        "extract_data_points",
        "summarize_content",
        "verify_claim_against_source",
    }
    # No duplicate names.
    assert len(names) == len(set(names))


def test_split_tools_have_distinct_nontrivial_descriptions() -> None:
    tools = td.split_analyze_document()
    descriptions = [t["description"] for t in tools]
    assert len(set(descriptions)) == 3, "split tools must have distinct descriptions"
    for desc in descriptions:
        assert len(desc) > 40, "each split tool needs a substantive description"
    # No two of the three split tools should read as ambiguous with each other.
    for i in range(len(tools)):
        for j in range(i + 1, len(tools)):
            assert td.describes_ambiguously(tools[i], tools[j]) is False


# --------------------------------------------------------------------------- #
# rename_for_web
# --------------------------------------------------------------------------- #
def test_rename_for_web() -> None:
    renamed = td.rename_for_web(BEFORE["analyze_content"])
    assert renamed["name"] == "extract_web_results"
    low = renamed["description"].lower()
    assert "web" in low, "renamed tool's description should be web-specific"
    assert renamed["description"] != BEFORE["analyze_content"]["description"]


# --------------------------------------------------------------------------- #
# describes_ambiguously
# --------------------------------------------------------------------------- #
def test_describes_ambiguously_flags_before_pair() -> None:
    assert td.describes_ambiguously(BEFORE["get_customer"], BEFORE["lookup_order"]) is True


def test_describes_ambiguously_clears_after_pair() -> None:
    after = _tools_after()
    assert td.describes_ambiguously(after["get_customer"], after["lookup_order"]) is False


# --------------------------------------------------------------------------- #
# tools_after.json deliverable
# --------------------------------------------------------------------------- #
def test_tools_after_is_disambiguated() -> None:
    after = _tools_after()
    # All six target tools present.
    assert {
        "get_customer",
        "lookup_order",
        "extract_data_points",
        "summarize_content",
        "verify_claim_against_source",
        "extract_web_results",
    } <= set(after)
    # The two historically confused tools carry rich, bounded descriptions.
    for name in ("get_customer", "lookup_order"):
        _has_required_elements(after[name]["description"])
    assert td.describes_ambiguously(after["get_customer"], after["lookup_order"]) is False


# --------------------------------------------------------------------------- #
# Optional semantic check (excluded by default; needs ANTHROPIC_API_KEY)
# --------------------------------------------------------------------------- #
@pytest.mark.llm
def test_descriptions_disambiguate_semantically() -> None:
    from grading import grade, require_llm

    require_llm()
    submission = (TARGET / "tools_after.json").read_text()
    verdict = grade(
        rubric=(
            "The SUBMISSION is a JSON array of tool definitions. Judge only the "
            "get_customer and lookup_order tools. PASS only if their descriptions "
            "make it unambiguous which single tool to call for (a) an order-status "
            "question such as 'Where is my order #88213?' -> lookup_order, and "
            "(b) a customer-profile question such as 'What email is on file for my "
            "account?' -> get_customer. The descriptions must state the input each "
            "accepts and include an explicit boundary distinguishing the two."
        ),
        submission=submission,
    )
    assert verdict["pass"], verdict["reason"]
