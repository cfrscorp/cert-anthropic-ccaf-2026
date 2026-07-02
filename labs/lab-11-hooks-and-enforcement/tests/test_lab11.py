"""Deterministic tests for L11 — Agent SDK Hooks & Workflow Enforcement.

These lock in the programmatic-enforcement contracts from Task Statements 1.5
(PostToolUse normalization, tool-call interception) and 1.4 (prerequisite gate,
structured handoff). Everything here is offline and deterministic — the whole
point of the lab is that these guarantees do not depend on a model call.

Run from labs/:  uv run pytest lab-11-hooks-and-enforcement
Validate ref:     LAB_TARGET=solution uv run pytest lab-11-hooks-and-enforcement
"""

from __future__ import annotations

from labkit import lab_module

hooks = lab_module(__file__, "hooks")


# --------------------------------------------------------------------------- #
# post_tool_use_normalize — Task Statement 1.5
# --------------------------------------------------------------------------- #

def test_normalize_unix_timestamp_to_iso():
    """A Unix epoch int becomes an ISO-8601 UTC string."""
    out = hooks.post_tool_use_normalize(
        "lookup_order", {"timestamp": 1719921600, "order_id": "A1"}
    )
    assert out["timestamp"] == "2024-07-02T12:00:00+00:00"
    assert out["order_id"] == "A1"          # other fields preserved
    assert out["source_tool"] == "lookup_order"


def test_normalize_iso_string_timestamp_is_canonicalized():
    """An ISO-8601 string with a trailing 'Z' is canonicalized to a UTC offset."""
    out = hooks.post_tool_use_normalize(
        "get_customer", {"timestamp": "2024-07-02T12:00:00Z"}
    )
    assert out["timestamp"] == "2024-07-02T12:00:00+00:00"


def test_normalize_numeric_status_code_to_label():
    """A numeric HTTP-style status code becomes a human-readable label."""
    ok = hooks.post_tool_use_normalize("process_refund", {"status": 200})
    err = hooks.post_tool_use_normalize("process_refund", {"status": 503})
    assert ok["status"] == "success"
    assert err["status"] == "server_error"


def test_normalize_all_three_formats_reach_one_canonical_shape():
    """Three tools with three representations converge on the same canonical shape."""
    a = hooks.post_tool_use_normalize("tool_a", {"timestamp": 1719921600, "status": 200})
    b = hooks.post_tool_use_normalize(
        "tool_b", {"timestamp": "2024-07-02T12:00:00Z", "status": "success"}
    )
    c = hooks.post_tool_use_normalize("tool_c", {"timestamp": 1719921600, "status": 201})
    assert a["timestamp"] == b["timestamp"] == c["timestamp"] == "2024-07-02T12:00:00+00:00"
    assert a["status"] == b["status"] == c["status"] == "success"


def test_normalize_does_not_mutate_input():
    """The hook returns a new dict; the raw result is untouched."""
    raw = {"timestamp": 1719921600, "status": 200}
    hooks.post_tool_use_normalize("lookup_order", raw)
    assert raw == {"timestamp": 1719921600, "status": 200}


# --------------------------------------------------------------------------- #
# intercept_tool_call — Task Statement 1.5
# --------------------------------------------------------------------------- #

def test_intercept_blocks_refund_over_limit():
    """A $600 refund exceeds the $500 limit: blocked and redirected to a human."""
    decision = hooks.intercept_tool_call("process_refund", {"amount": 600})
    assert decision["action"] == "block"
    assert decision["redirect"] == "escalate_to_human"
    assert "reason" in decision and decision["reason"]


def test_intercept_allows_refund_within_limit():
    """A $400 refund is within the limit and is allowed."""
    decision = hooks.intercept_tool_call("process_refund", {"amount": 400})
    assert decision == {"action": "allow"}


def test_intercept_respects_configurable_limit():
    """The ceiling is configurable; $400 blocks under a $300 limit."""
    decision = hooks.intercept_tool_call("process_refund", {"amount": 400}, refund_limit=300)
    assert decision["action"] == "block"


def test_intercept_ignores_non_refund_tools():
    """A large amount on a different tool is not the refund policy's concern."""
    decision = hooks.intercept_tool_call("lookup_order", {"amount": 9999})
    assert decision == {"action": "allow"}


# --------------------------------------------------------------------------- #
# PrerequisiteGate — Task Statement 1.4 / Sample Question 1
# --------------------------------------------------------------------------- #

def test_gate_blocks_refund_before_get_customer():
    """process_refund is blocked before get_customer has verified identity."""
    gate = hooks.PrerequisiteGate()
    assert gate.check("process_refund") is False


def test_gate_allows_refund_after_verified_customer():
    """A verified get_customer result unlocks process_refund."""
    gate = hooks.PrerequisiteGate()
    gate.record_tool_result("get_customer", {"customer_id": "C-42", "verified": True})
    assert gate.check("process_refund") is True
    assert gate.verified_customer_id == "C-42"


def test_gate_stays_locked_on_unverified_customer():
    """An unverified get_customer result must NOT unlock the gate."""
    gate = hooks.PrerequisiteGate()
    gate.record_tool_result("get_customer", {"customer_id": "C-42", "verified": False})
    assert gate.check("process_refund") is False


def test_gate_allows_prerequisite_tool_itself():
    """The prerequisite tool (get_customer) is never gated."""
    gate = hooks.PrerequisiteGate()
    assert gate.check("get_customer") is True


# --------------------------------------------------------------------------- #
# build_handoff — Task Statement 1.4
# --------------------------------------------------------------------------- #

def test_build_handoff_includes_all_required_fields():
    """The handoff carries every fact a human needs without the transcript."""
    context = {
        "customer_id": "C-42",
        "root_cause": "Damaged item, refund exceeds auto-approval limit.",
        "refund_amount": 600,
        "recommended_action": "Approve full refund and issue apology credit.",
    }
    handoff = hooks.build_handoff(context)
    for field in ("customer_id", "root_cause", "refund_amount", "recommended_action"):
        assert field in handoff
    assert handoff["customer_id"] == "C-42"
    assert handoff["refund_amount"] == 600
    assert handoff["escalated_to"] == "human"


def test_build_handoff_surfaces_missing_fields_as_none():
    """Missing context is surfaced as None, not silently dropped."""
    handoff = hooks.build_handoff({"customer_id": "C-7"})
    assert handoff["customer_id"] == "C-7"
    assert handoff["root_cause"] is None
    assert handoff["refund_amount"] is None
    assert handoff["recommended_action"] is None
