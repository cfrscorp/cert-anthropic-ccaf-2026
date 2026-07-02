"""Deterministic tests for L08 — Plan Mode, Direct Execution & Iterative Refinement.

These exercise the judgment calls from Task Statements 3.4 and 3.5:
    - choose_mode(task)           -> "plan" | "direct"
    - should_use_explore(task)    -> bool
    - refinement_strategy(issues) -> "single_message" | "sequential"

The MODE_SCENARIOS and REFINEMENT_SCENARIOS tables below mirror
``scenarios.md`` exactly — that markdown file is the single source of truth for
the canonical cases; if you edit one, edit the other.

Run from labs/:  uv run pytest lab-08-plan-mode-and-refinement
Validate ref:     LAB_TARGET=solution uv run pytest lab-08-plan-mode-and-refinement
"""

from __future__ import annotations

import pytest
from labkit import lab_module

decisions = lab_module(__file__, "decisions")


# ---------------------------------------------------------------------------
# Canonical mode + explore scenarios (mirror scenarios.md, "Mode + Explore").
# Each entry: (id, task, expected_mode, expected_explore)
# ---------------------------------------------------------------------------
MODE_SCENARIOS = [
    (
        "monolith-to-microservices",
        {
            "multi_file_count": 60,
            "architectural": True,
            "multiple_valid_approaches": True,
            "clear_scope": False,
            "verbose_discovery": True,
            "multi_phase": True,
            "context_exhaustion_risk": True,
        },
        "plan",
        True,
    ),
    (
        "single-file-bugfix-stack-trace",
        {
            "multi_file_count": 1,
            "architectural": False,
            "multiple_valid_approaches": False,
            "clear_scope": True,
            "verbose_discovery": False,
            "multi_phase": False,
            "context_exhaustion_risk": False,
        },
        "direct",
        False,
    ),
    (
        "add-date-validation-conditional",
        {
            "multi_file_count": 1,
            "architectural": False,
            "multiple_valid_approaches": False,
            "clear_scope": True,
            "verbose_discovery": False,
            "multi_phase": False,
            "context_exhaustion_risk": False,
        },
        "direct",
        False,
    ),
    (
        "library-migration-45-files",
        {
            "multi_file_count": 45,
            "architectural": False,
            "multiple_valid_approaches": True,
            "clear_scope": False,
            "verbose_discovery": True,
            "multi_phase": True,
            "context_exhaustion_risk": True,
        },
        "plan",
        True,
    ),
    (
        "choose-integration-approach",
        {
            "multi_file_count": 2,
            "architectural": True,
            "multiple_valid_approaches": True,
            "clear_scope": False,
            "verbose_discovery": False,
            "multi_phase": False,
            "context_exhaustion_risk": False,
        },
        "plan",
        False,
    ),
    (
        "add-null-guard-one-function",
        {
            "multi_file_count": 1,
            "architectural": False,
            "multiple_valid_approaches": False,
            "clear_scope": True,
            "verbose_discovery": False,
            "multi_phase": False,
            "context_exhaustion_risk": False,
        },
        "direct",
        False,
    ),
    (
        "execute-planned-migration-step",
        {
            "multi_file_count": 1,
            "architectural": False,
            "multiple_valid_approaches": False,
            "clear_scope": True,
            "verbose_discovery": False,
            "multi_phase": False,
            "context_exhaustion_risk": False,
        },
        "direct",
        False,
    ),
    (
        "map-unfamiliar-codebase",
        {
            "multi_file_count": 1,
            "architectural": False,
            "multiple_valid_approaches": False,
            "clear_scope": False,
            "verbose_discovery": True,
            "multi_phase": True,
            "context_exhaustion_risk": True,
        },
        "plan",
        True,
    ),
]


# ---------------------------------------------------------------------------
# Canonical refinement scenarios (mirror scenarios.md, "Refinement scenarios").
# Each entry: (id, issues, expected_strategy)
# ---------------------------------------------------------------------------
REFINEMENT_SCENARIOS = [
    (
        "coupled-lock-and-race",
        [{"interacts_with_others": True}, {"interacts_with_others": True}],
        "single_message",
    ),
    (
        "independent-typo-and-docstring",
        [{"interacts_with_others": False}, {"interacts_with_others": False}],
        "sequential",
    ),
    (
        "schema-and-serializer-coupled",
        [{"interacts_with_others": True}, {"interacts_with_others": False}],
        "single_message",
    ),
    (
        "three-independent-lint-fixes",
        [
            {"interacts_with_others": False},
            {"interacts_with_others": False},
            {"interacts_with_others": False},
        ],
        "sequential",
    ),
    (
        "no-issues",
        [],
        "sequential",
    ),
]


# ---------------------------------------------------------------------------
# choose_mode
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "task, expected_mode",
    [(task, mode) for _id, task, mode, _explore in MODE_SCENARIOS],
    ids=[_id for _id, *_ in MODE_SCENARIOS],
)
def test_choose_mode_matches_canonical(task, expected_mode):
    assert decisions.choose_mode(task) == expected_mode


def test_monolith_restructuring_is_plan_mode():
    """Sample Question 5: complexity is stated up front → plan mode, not direct."""
    task = dict(MODE_SCENARIOS[0][1])  # monolith-to-microservices
    assert decisions.choose_mode(task) == "plan"


def test_single_file_bugfix_is_direct_execution():
    """A single-file fix with a clear stack trace has no plan triggers → direct."""
    task = dict(MODE_SCENARIOS[1][1])  # single-file-bugfix-stack-trace
    assert decisions.choose_mode(task) == "direct"


def test_multi_file_alone_forces_plan():
    """Even without architectural/approach flags, >1 file is a plan trigger."""
    assert (
        decisions.choose_mode(
            {
                "multi_file_count": 3,
                "architectural": False,
                "multiple_valid_approaches": False,
                "clear_scope": True,
            }
        )
        == "plan"
    )


def test_unclear_scope_alone_forces_plan():
    """Open-ended scope on a single file still warrants planning."""
    assert (
        decisions.choose_mode(
            {
                "multi_file_count": 1,
                "architectural": False,
                "multiple_valid_approaches": False,
                "clear_scope": False,
            }
        )
        == "plan"
    )


# ---------------------------------------------------------------------------
# should_use_explore
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "task, expected_explore",
    [(task, explore) for _id, task, _mode, explore in MODE_SCENARIOS],
    ids=[_id for _id, *_ in MODE_SCENARIOS],
)
def test_should_use_explore_matches_canonical(task, expected_explore):
    assert decisions.should_use_explore(task) is expected_explore


def test_verbose_discovery_without_burden_is_not_explore():
    """Verbose discovery that is neither multi-phase nor context-risky → no subagent."""
    assert (
        decisions.should_use_explore(
            {
                "verbose_discovery": True,
                "multi_phase": False,
                "context_exhaustion_risk": False,
            }
        )
        is False
    )


def test_multi_phase_without_verbose_discovery_is_not_explore():
    """No verbose discovery to isolate → Explore overhead is not warranted."""
    assert (
        decisions.should_use_explore(
            {
                "verbose_discovery": False,
                "multi_phase": True,
                "context_exhaustion_risk": True,
            }
        )
        is False
    )


# ---------------------------------------------------------------------------
# refinement_strategy
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "issues, expected_strategy",
    [(issues, strat) for _id, issues, strat in REFINEMENT_SCENARIOS],
    ids=[_id for _id, *_ in REFINEMENT_SCENARIOS],
)
def test_refinement_strategy_matches_canonical(issues, expected_strategy):
    assert decisions.refinement_strategy(issues) == expected_strategy


def test_interacting_issues_use_single_message():
    assert (
        decisions.refinement_strategy([{"interacts_with_others": True}])
        == "single_message"
    )


def test_independent_issues_use_sequential():
    assert (
        decisions.refinement_strategy(
            [{"interacts_with_others": False}, {"interacts_with_others": False}]
        )
        == "sequential"
    )
