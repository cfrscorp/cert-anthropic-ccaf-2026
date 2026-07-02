"""Deterministic tests for L22 — Capstone: Customer Support Resolution Agent.

These lock in the integrated behaviour of the whole agent (Scenario 1 /
Preparation Exercise 1). Everything is offline: the Claude client is a scripted
``MockAnthropic`` whose responses drive the agentic loop, while the guardrails
enforce their guarantees in code regardless of what the model asks for.

Run from labs/:  uv run pytest lab-22-capstone-support-agent
Validate ref:     LAB_TARGET=solution uv run pytest lab-22-capstone-support-agent
"""

from __future__ import annotations

from labkit import lab_module
from mock_anthropic import MockAnthropic, text_response, tool_use_response

tools = lab_module(__file__, "tools")
guardrails = lab_module(__file__, "guardrails")
agent = lab_module(__file__, "support_agent")

CUST = "CUST-40912"


def _backends():
    return tools.default_backends()


def _find(tool_calls, name, *, blocked=None):
    for tc in tool_calls:
        if tc["name"] != name:
            continue
        if blocked is not None and tc["blocked"] is not blocked:
            continue
        return tc
    return None


# --------------------------------------------------------------------------- #
# Pure helpers: case facts (5.1) and concern decomposition (1.4)
# --------------------------------------------------------------------------- #
def test_extract_case_facts_retains_amounts_order_status():
    """Case facts preserve amounts, dates, order numbers, and statuses verbatim."""
    facts = agent.extract_case_facts([
        "Refund $129.99 on order ORD-88213 which shipped 2026-07-05.",
    ])
    assert "$129.99" in facts["amounts"]
    assert "ORD-88213" in facts["order_numbers"]
    assert "shipped" in facts["statuses"]
    assert "2026-07-05" in facts["dates"]


def test_decompose_multi_vs_single_concern():
    """A two-issue message splits into two concerns; a one-issue message stays one."""
    multi = agent.decompose_concerns(
        "Where is my order ORD-88213? Also, I need a refund for the charger."
    )
    assert len(multi) >= 2
    single = agent.decompose_concerns("Where is my order ORD-88213?")
    assert len(single) == 1


# --------------------------------------------------------------------------- #
# Guardrail units (self-contained reimplementation of L11/L12 ideas)
# --------------------------------------------------------------------------- #
def test_prerequisite_gate_blocks_until_verified():
    gate = guardrails.PrerequisiteGate()
    assert gate.check("lookup_order") is False
    assert gate.check("process_refund") is False
    gate.record_tool_result("get_customer", {"customer_id": CUST, "verified": True})
    assert gate.check("lookup_order") is True
    assert gate.check("process_refund") is True
    assert gate.verified_customer_id == CUST


def test_prerequisite_gate_stays_locked_on_unverified():
    gate = guardrails.PrerequisiteGate()
    gate.record_tool_result("get_customer", {"customer_id": CUST, "verified": False})
    assert gate.check("process_refund") is False


def test_intercept_blocks_over_limit_and_allows_within():
    assert guardrails.intercept_tool_call("process_refund", {"amount": 600})["action"] == "block"
    assert guardrails.intercept_tool_call("process_refund", {"amount": 400}) == {"action": "allow"}
    assert guardrails.intercept_tool_call("lookup_order", {"amount": 9999}) == {"action": "allow"}


def test_wants_human_matches_explicit_only():
    assert guardrails.wants_human("Please let me speak to a human.") is True
    assert guardrails.wants_human("I want a human agent now") is True
    assert guardrails.wants_human("Where is my order ORD-88213?") is False


def test_build_handoff_surfaces_missing_as_none():
    handoff = guardrails.build_handoff({"customer_id": CUST, "refund_amount": 600})
    assert handoff["customer_id"] == CUST
    assert handoff["refund_amount"] == 600
    assert handoff["root_cause"] is None
    assert handoff["escalated_to"] == "human"


# --------------------------------------------------------------------------- #
# Structured tool errors (2.2) at the tool layer
# --------------------------------------------------------------------------- #
def test_make_error_marks_only_transient_retryable():
    assert tools.make_error("transient", "timeout")["isRetryable"] is True
    assert tools.make_error("business", "over limit")["isRetryable"] is False


def test_lookup_missing_order_is_empty_not_error():
    """A no-match lookup is a valid empty result, not an access failure (5.3)."""
    res = tools.execute_tool("lookup_order", {"order_id": "ORD-00000"}, _backends())
    assert res.get("found") is False
    assert res.get("isError") is not True


# --------------------------------------------------------------------------- #
# End-to-end: prerequisite gate (1.4 / SQ1)
# --------------------------------------------------------------------------- #
def test_refuses_order_ops_before_get_customer():
    """lookup_order attempted first is refused; it succeeds only after get_customer."""
    responses = [
        tool_use_response("lookup_order", {"order_id": "ORD-88213"}),   # blocked by gate
        tool_use_response("get_customer", {"customer_id": CUST}),        # verifies identity
        tool_use_response("lookup_order", {"order_id": "ORD-88213"}),   # now allowed
        text_response("Your order ORD-88213 has shipped; arriving 2026-07-05."),
    ]
    client = MockAnthropic(responses=responses)
    out = agent.run_support_agent(client, "Where is my order ORD-88213?", _backends())

    assert out["tool_calls"][0]["name"] == "lookup_order"
    assert out["tool_calls"][0]["blocked"] is True
    assert out["tool_calls"][0]["reason"] == "prerequisite"

    names = [tc["name"] for tc in out["tool_calls"]]
    got_customer = names.index("get_customer")
    ok_lookup = next(
        i for i, tc in enumerate(out["tool_calls"])
        if tc["name"] == "lookup_order" and tc["blocked"] is False
    )
    assert got_customer < ok_lookup            # identity verified before the order op
    assert out["verified_customer_id"] == CUST
    assert out["escalated"] is False
    # The loop forwarded the real tool schemas and a system prompt each turn.
    assert client.calls[0]["tools"] == tools.TOOLS
    assert "escalate" in client.calls[0]["system"].lower()


# --------------------------------------------------------------------------- #
# End-to-end: refund interception (1.5)
# --------------------------------------------------------------------------- #
def test_refund_over_limit_blocked_and_escalated():
    """A $600 refund is intercepted, escalated, and no money moves."""
    backends = _backends()
    responses = [
        tool_use_response("get_customer", {"customer_id": CUST}),
        tool_use_response("process_refund", {"order_id": "ORD-55100", "amount": 600, "reason": "damaged"}),
        text_response("That amount is above my limit, so I've escalated it to a human agent."),
    ]
    out = agent.run_support_agent(
        MockAnthropic(responses=responses),
        "I need a $600 refund for my damaged order ORD-55100.",
        backends,
    )
    assert out["escalated"] is True
    assert out["escalation_reason"] == "refund_over_limit"
    assert out["handoff"]["refund_amount"] == 600
    assert out["handoff"]["customer_id"] == CUST
    refund_tc = _find(out["tool_calls"], "process_refund")
    assert refund_tc["blocked"] is True
    assert backends["refunds"] == []           # blocked before execution — nothing recorded


def test_refund_within_limit_proceeds():
    """A $400 refund is under the ceiling and is processed normally."""
    backends = _backends()
    responses = [
        tool_use_response("get_customer", {"customer_id": CUST}),
        tool_use_response("process_refund", {"order_id": "ORD-55100", "amount": 400, "reason": "damaged"}),
        text_response("Done — I've refunded $400 to your original payment method."),
    ]
    out = agent.run_support_agent(
        MockAnthropic(responses=responses),
        "Please refund $400 for the damage on order ORD-55100.",
        backends,
    )
    assert out["escalation_reason"] != "refund_over_limit"
    refund_tc = _find(out["tool_calls"], "process_refund", blocked=False)
    assert refund_tc is not None
    assert refund_tc["result"]["status"] == "refunded"
    assert refund_tc["result"]["amount"] == 400
    assert len(backends["refunds"]) == 1


# --------------------------------------------------------------------------- #
# End-to-end: escalation & ambiguity (5.2)
# --------------------------------------------------------------------------- #
def test_explicit_human_request_escalates_immediately():
    """An explicit human request escalates with NO prior investigation."""
    client = MockAnthropic(responses=[])       # must never be called
    out = agent.run_support_agent(
        client,
        "This is ridiculous, I want to speak to a human right now.",
        _backends(),
    )
    assert out["escalated"] is True
    assert out["escalation_reason"] == "explicit_human_request"
    assert out["handoff"] is not None
    assert out["tool_calls"] == []             # no investigation tools ran
    assert client.calls == []                  # the model was not even called
    assert out["iterations"] == 0


def test_multiple_matches_asks_for_identifier():
    """A name matching two accounts triggers a clarification, not a guess."""
    responses = [
        tool_use_response("get_customer", {"name": "Sam Taylor"}),
        text_response("I found more than one account under that name — could you share your customer ID (CUST-...)?"),
    ]
    out = agent.run_support_agent(
        MockAnthropic(responses=responses),
        "Hi, it's Sam Taylor — where's my refund?",
        _backends(),
    )
    assert out["clarification_requested"] is True
    assert out["verified_customer_id"] is None
    gc = _find(out["tool_calls"], "get_customer")
    assert gc["result"]["match_count"] == 2
    assert _find(out["tool_calls"], "process_refund") is None
    assert _find(out["tool_calls"], "lookup_order") is None
    assert out["escalated"] is False


# --------------------------------------------------------------------------- #
# End-to-end: multi-concern decomposition (1.4)
# --------------------------------------------------------------------------- #
def test_multi_concern_message_decomposed_and_both_addressed():
    """Two issues in one message are decomposed and both investigated."""
    msg = (
        "Where is my order ORD-88213? Also, I need a $40 refund for the damaged "
        "charger on order ORD-55100."
    )
    responses = [
        tool_use_response("get_customer", {"customer_id": CUST}),
        tool_use_response("lookup_order", {"order_id": "ORD-88213"}),
        tool_use_response("process_refund", {"order_id": "ORD-55100", "amount": 40, "reason": "damaged charger"}),
        text_response("Your order ORD-88213 has shipped (arriving 2026-07-05), and I've refunded $40 for the charger."),
    ]
    out = agent.run_support_agent(MockAnthropic(responses=responses), msg, _backends())
    assert len(out["concerns"]) >= 2
    assert _find(out["tool_calls"], "lookup_order", blocked=False) is not None
    assert _find(out["tool_calls"], "process_refund", blocked=False) is not None
    assert out["escalated"] is False
    assert "ORD-88213" in out["final_text"]


# --------------------------------------------------------------------------- #
# End-to-end: persistent case facts (5.1)
# --------------------------------------------------------------------------- #
def test_case_facts_persist_across_tool_results():
    """The case-facts block captures the order#, amount, and status from a lookup."""
    responses = [
        tool_use_response("get_customer", {"customer_id": CUST}),
        tool_use_response("lookup_order", {"order_id": "ORD-88213"}),
        text_response("Your order ORD-88213 has shipped and will arrive 2026-07-05."),
    ]
    out = agent.run_support_agent(
        MockAnthropic(responses=responses), "Where is my order ORD-88213?", _backends()
    )
    facts = out["case_facts"]
    assert "ORD-88213" in facts["order_numbers"]
    assert "shipped" in facts["statuses"]
    assert "$129.99" in facts["amounts"]        # value came from the tool result, not the message


# --------------------------------------------------------------------------- #
# End-to-end: structured errors — retry transient, explain business (2.2)
# --------------------------------------------------------------------------- #
def test_transient_tool_error_is_retried():
    """A transient tool error is retried locally and then succeeds."""
    backends = _backends()
    state = {"n": 0}

    def flaky_lookup(tool_input):
        state["n"] += 1
        if state["n"] == 1:
            return tools.make_error("transient", "temporary timeout contacting order service")
        return {"found": True, "order_id": tool_input["order_id"], "status": "shipped",
                "order_total": "$129.99"}

    backends["lookup_order"] = flaky_lookup
    responses = [
        tool_use_response("get_customer", {"customer_id": CUST}),
        tool_use_response("lookup_order", {"order_id": "ORD-88213"}),
        text_response("Your order ORD-88213 has shipped."),
    ]
    out = agent.run_support_agent(MockAnthropic(responses=responses), "Where is order ORD-88213?", backends)
    lookup_tc = _find(out["tool_calls"], "lookup_order", blocked=False)
    assert lookup_tc["attempts"] == 2
    assert lookup_tc["result"]["found"] is True
    assert state["n"] == 2


def test_business_error_is_explained_not_retried():
    """A business error (ineligible refund) is not retried; the agent explains it."""
    backends = _backends()                       # ORD-99999 is refund_eligible=False
    responses = [
        tool_use_response("get_customer", {"customer_id": CUST}),
        tool_use_response("process_refund", {"order_id": "ORD-99999", "amount": 40, "reason": "damaged"}),
        text_response("I can't refund ORD-99999 because it was already refunded on 2026-06-20."),
    ]
    out = agent.run_support_agent(MockAnthropic(responses=responses), "Refund $40 on ORD-99999 please.", backends)
    refund_tc = _find(out["tool_calls"], "process_refund", blocked=False)
    assert refund_tc["result"]["errorCategory"] == "business"
    assert refund_tc["result"]["isRetryable"] is False
    assert refund_tc["attempts"] == 1            # not retried
    assert out["escalated"] is False
    assert "refund" in out["final_text"].lower()
