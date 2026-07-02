"""Deterministic tests for L09 — Structured Error Responses & Tool Distribution.

Runs against starter/ by default (learner's work, expected to fail on the
NotImplementedError stubs) and solution/ when LAB_TARGET=solution (must be
green). Fully offline: no live Claude call; the one MockAnthropic test uses the
shared deterministic mock.
"""

from __future__ import annotations

import pytest

from labkit import lab_module
from mock_anthropic import MockAnthropic, tool_use_response

errors = lab_module(__file__, "errors")
tdist = lab_module(__file__, "tool_distribution")


# ===================== errors.py: make_error / is_retryable ================= #
def test_make_error_shape() -> None:
    err = errors.make_error("transient", "Upstream timed out; try again.")
    assert err["isError"] is True
    assert err["errorCategory"] == "transient"
    assert err["isRetryable"] is True
    assert err["message"] == "Upstream timed out; try again."
    # Exactly the four MCP fields, nothing generic like {"error": "failed"}.
    assert set(err) == {"isError", "errorCategory", "isRetryable", "message"}


def test_make_error_requires_valid_category() -> None:
    with pytest.raises(ValueError):
        errors.make_error("kaboom", "nope")


def test_make_error_requires_message() -> None:
    with pytest.raises(ValueError):
        errors.make_error("business", "   ")


@pytest.mark.parametrize(
    "category,expected",
    [
        ("transient", True),
        ("validation", False),
        ("business", False),
        ("permission", False),
    ],
)
def test_is_retryable_matrix(category: str, expected: bool) -> None:
    assert errors.is_retryable(category) is expected
    # And make_error's default isRetryable follows is_retryable.
    err = errors.make_error(category, "some human-readable explanation")
    assert err["isRetryable"] is expected


def test_transient_retryable_business_not() -> None:
    transient = errors.make_error("transient", "Service unavailable.")
    business = errors.make_error(
        "business", "Refund of $750 exceeds the $500 auto-approval limit."
    )
    assert transient["isRetryable"] is True
    assert business["isRetryable"] is False


def test_retryable_override() -> None:
    # A transient error whose retries are already exhausted can be marked False.
    err = errors.make_error("transient", "Timed out after 3 retries.", retryable=False)
    assert err["errorCategory"] == "transient"
    assert err["isRetryable"] is False


def test_is_retryable_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        errors.is_retryable("nonsense")


# ===================== errors.py: classify ================================== #
@pytest.mark.parametrize(
    "exc,expected",
    [
        (TimeoutError("upstream timed out"), "transient"),
        (ConnectionError("connection reset"), "transient"),
        (PermissionError("not allowed"), "permission"),
        (ValueError("invalid order id"), "validation"),
    ],
)
def test_classify_exceptions(exc: Exception, expected: str) -> None:
    assert errors.classify(exc) == expected


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("timeout", "transient"),
        ("service unavailable", "transient"),
        ("invalid input", "validation"),
        ("policy violation", "business"),
        ("refund exceeds the $500 limit", "business"),
        ("unauthorized", "permission"),
        ("403 forbidden", "permission"),
        ("transient", "transient"),
        ("business", "business"),
    ],
)
def test_classify_kind_strings(kind: str, expected: str) -> None:
    assert errors.classify(kind) == expected


def test_classify_always_returns_a_category() -> None:
    assert errors.classify("something entirely unlabelled") in errors.CATEGORIES


# ===================== errors.py: empty vs access failure =================== #
def test_empty_result_is_not_a_failure() -> None:
    # A successful query that found nothing is "empty", NOT a failure.
    assert errors.is_empty_result_vs_failure({"results": []}) == "empty"
    assert errors.is_empty_result_vs_failure([]) == "empty"
    assert errors.is_empty_result_vs_failure({"matches": [], "status": "ok"}) == "empty"


def test_populated_result_is_results() -> None:
    assert errors.is_empty_result_vs_failure({"results": [{"id": 1}]}) == "results"
    assert errors.is_empty_result_vs_failure(["a", "b"]) == "results"


def test_access_failure_detected() -> None:
    err = errors.make_error("transient", "Search backend unavailable.")
    assert errors.is_empty_result_vs_failure(err) == "access_failure"
    assert errors.is_empty_result_vs_failure({"status": "error"}) == "access_failure"
    assert errors.is_empty_result_vs_failure({"ok": False}) == "access_failure"
    # None returned in place of a result is a failure to surface, not an answer.
    assert errors.is_empty_result_vs_failure(None) == "access_failure"


# ===================== tool_distribution.py: assign_tools =================== #
ALL = tdist.ALL_RESEARCH_TOOLS
EXPECTED_ROLES = ("coordinator", "searcher", "analyst", "synthesis", "writer")


def test_all_catalogue_is_overprovisioned() -> None:
    # The full catalogue is the anti-pattern: too many tools for one agent.
    assert len(ALL) >= 18
    assert tdist.is_overprovisioned(ALL) is True


def test_assign_tools_restricts_to_role() -> None:
    searcher = tdist.assign_tools("searcher", ALL)
    names = {t["name"] for t in searcher}
    # Gets its own search tools...
    assert "web_search" in names
    # ...and NOT another role's tools (no cross-specialization misuse).
    assert "generate_report" not in names
    assert "synthesize_findings" not in names
    # Scoped set is small and a strict subset of the catalogue.
    assert tdist.is_overprovisioned(searcher) is False
    assert names <= {t["name"] for t in ALL}


def test_assign_tools_synthesis_excludes_web_search() -> None:
    synth = tdist.assign_tools("synthesis", ALL)
    names = {t["name"] for t in synth}
    # A synthesis agent must not be handed web-search tools (Sample Question 9).
    assert "web_search" not in names
    assert "synthesize_findings" in names


def test_assign_tools_drops_deprecated_generic_tool() -> None:
    # The generic fetch_url was replaced by the constrained load_document; no
    # role should be assigned fetch_url.
    for role in EXPECTED_ROLES:
        names = {t["name"] for t in tdist.assign_tools(role, ALL)}
        assert "fetch_url" not in names


def test_assign_tools_unknown_role() -> None:
    with pytest.raises(ValueError):
        tdist.assign_tools("nope", ALL)


def test_is_overprovisioned_clears_scoped_set() -> None:
    for role in EXPECTED_ROLES:
        scoped = tdist.assign_tools(role, ALL)
        assert 1 <= len(scoped) <= tdist.MAX_RECOMMENDED_TOOLS
        assert tdist.is_overprovisioned(scoped) is False


# ===================== tool_distribution.py: cross-role tool ================ #
def test_add_scoped_cross_role_tool_for_synthesis() -> None:
    agent = {"role": "synthesis", "tools": list(tdist.assign_tools("synthesis", ALL))}
    verify = next(t for t in ALL if t["name"] == "verify_fact")
    updated = tdist.add_scoped_cross_role_tool(agent, verify)
    names = {t["name"] for t in updated["tools"]}
    assert "verify_fact" in names
    # Still scoped — one high-frequency cross-role tool, not the whole catalogue.
    assert tdist.is_overprovisioned(updated["tools"]) is False


def test_add_scoped_cross_role_tool_is_idempotent() -> None:
    agent = {"role": "synthesis", "tools": []}
    once = tdist.add_scoped_cross_role_tool(agent, "verify_fact")
    twice = tdist.add_scoped_cross_role_tool(once, "verify_fact")
    assert [tdist._tool_name(t) for t in twice["tools"]].count("verify_fact") == 1


def test_add_scoped_cross_role_tool_rejects_non_allowlisted() -> None:
    # Handing synthesis a full web_search tool would over-provision it.
    agent = {"role": "synthesis", "tools": []}
    with pytest.raises(ValueError):
        tdist.add_scoped_cross_role_tool(agent, "web_search")


# ===================== tool_distribution.py: tool_choice =================== #
def test_choose_tool_choice_conversational_is_auto() -> None:
    assert tdist.choose_tool_choice("conversational") == "auto"


def test_choose_tool_choice_unknown_schema_is_any() -> None:
    assert tdist.choose_tool_choice("unknown_schema") == "any"


def test_choose_tool_choice_force_is_specific_tool() -> None:
    choice = tdist.choose_tool_choice("force_extract_metadata_first")
    assert choice == {"type": "tool", "name": "extract_metadata"}


def test_choose_tool_choice_force_dict_form() -> None:
    assert tdist.choose_tool_choice({"force": "get_customer"}) == {
        "type": "tool",
        "name": "get_customer",
    }


def test_choose_tool_choice_unknown_scenario_raises() -> None:
    with pytest.raises(ValueError):
        tdist.choose_tool_choice("who knows")


# ===================== MockAnthropic: tool_choice is forwarded ============== #
def test_forced_tool_choice_is_forwarded_to_client() -> None:
    client = MockAnthropic(responses=[tool_use_response("extract_metadata", {})])
    resp = tdist.run_forced_tool_call(
        client,
        "force_extract_metadata_first",
        messages=[{"role": "user", "content": "here is a document"}],
        tools=ALL,
    )
    # The forced tool_choice actually reached the API call.
    assert client.calls[-1]["tool_choice"] == {"type": "tool", "name": "extract_metadata"}
    assert resp.tool_use_blocks()[0].name == "extract_metadata"
