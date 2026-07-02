"""Capstone reference — the programmatic-enforcement layer.

These are the *deterministic* guarantees that wrap the agentic loop. The exam is
emphatic (Task Statements 1.4 and 1.5, Sample Question 1) that when a rule has
financial or identity consequences, code-level enforcement beats a prompt
instruction, because a prompt has a non-zero failure rate.

Four primitives:

* :class:`PrerequisiteGate` — blocks ``lookup_order`` / ``process_refund`` until
  ``get_customer`` has returned a *verified* ``customer_id``. This is the
  programmatic answer to Sample Question 1 (a gate, not a stronger prompt).
* :func:`intercept_tool_call` — an outgoing-call interception hook that blocks a
  ``process_refund`` above the policy ceiling and redirects it to human
  escalation, on every call regardless of the prompt.
* :func:`build_handoff` — compiles a structured escalation summary for a human
  who cannot see the conversation transcript.
* :func:`wants_human` — detects an explicit request for a human so the agent can
  honour it *immediately, without first investigating* (Task Statement 5.2).

Self-contained (the capstone imports no other lab). Imported module — docstrings
required, exempt from the PEP 723 / argparse script conventions.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "REFUND_LIMIT",
    "PrerequisiteGate",
    "intercept_tool_call",
    "build_handoff",
    "wants_human",
    "HUMAN_REQUEST_MARKERS",
]

# Default auto-approval ceiling. A refund strictly greater than this is blocked.
REFUND_LIMIT: float = 500


# --------------------------------------------------------------------------- #
# Prerequisite gate (Task Statement 1.4 / Sample Question 1)
# --------------------------------------------------------------------------- #
class PrerequisiteGate:
    """Blocks account-specific tools until identity is verified by get_customer.

    Sample Question 1: the agent sometimes skips ``get_customer`` and refunds the
    wrong account. The correct fix is a programmatic prerequisite (option A), not
    a stronger prompt (B) or more few-shot examples (C) — both only lower a
    probabilistic failure rate. This gate makes the unsafe path impossible.

        gate = PrerequisiteGate()
        assert gate.check("lookup_order") is False       # nothing verified yet
        gate.record_tool_result("get_customer",
                                {"customer_id": "C-42", "verified": True})
        assert gate.check("lookup_order") is True
    """

    def __init__(
        self,
        *,
        protected_tools: tuple[str, ...] = ("lookup_order", "process_refund"),
        prerequisite_tool: str = "get_customer",
    ) -> None:
        self._protected_tools = tuple(protected_tools)
        self._prerequisite_tool = prerequisite_tool
        self._verified_customer_id: str | None = None

    @property
    def verified_customer_id(self) -> str | None:
        """The verified customer id recorded so far, or ``None`` if unset."""
        return self._verified_customer_id

    def record_tool_result(self, name: str, result: dict[str, Any]) -> None:
        """Unlock the gate only on a verified prerequisite result.

        A ``get_customer`` result unlocks the gate only when it carries a truthy
        ``customer_id`` AND ``verified is True``. A multi-match or no-match result
        (verified false) leaves the gate closed, so the agent cannot act on an
        ambiguous identity.
        """
        if name != self._prerequisite_tool:
            return
        customer_id = result.get("customer_id")
        if customer_id and result.get("verified") is True:
            self._verified_customer_id = customer_id

    def check(self, tool_name: str) -> bool:
        """Return whether ``tool_name`` may run right now."""
        if tool_name in self._protected_tools:
            return self._verified_customer_id is not None
        return True


# --------------------------------------------------------------------------- #
# Tool-call interception hook (Task Statement 1.5)
# --------------------------------------------------------------------------- #
def intercept_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    refund_limit: float = REFUND_LIMIT,
) -> dict[str, Any]:
    """Allow a tool call, or block an over-limit refund and redirect to a human.

    A ``process_refund`` whose amount (from ``"amount"`` or ``"refund_amount"``)
    strictly exceeds ``refund_limit`` is blocked. Enforcing this in a hook makes
    the ceiling deterministic — it holds no matter how the model was prompted.

    Returns ``{"action": "allow"}`` or
    ``{"action": "block", "redirect": "escalate_to_human", "reason": ...}``.
    """
    if tool_name == "process_refund":
        amount = tool_input.get("amount", tool_input.get("refund_amount", 0)) or 0
        if amount > refund_limit:
            return {
                "action": "block",
                "redirect": "escalate_to_human",
                "reason": (
                    f"Refund of ${amount} exceeds the ${refund_limit} "
                    "auto-approval limit; redirecting to human escalation."
                ),
            }
    return {"action": "allow"}


# --------------------------------------------------------------------------- #
# Structured handoff (Task Statement 1.4)
# --------------------------------------------------------------------------- #
def build_handoff(context: dict[str, Any]) -> dict[str, Any]:
    """Compile a structured escalation summary for a human agent.

    The human has no access to the transcript, so the handoff carries who the
    customer is, the root cause, the money involved, and the recommended action.
    Recognised keys are ``customer_id``, ``root_cause``, ``refund_amount`` and
    ``recommended_action``; any missing key is surfaced as ``None`` (never
    silently dropped) so the receiving human sees exactly what is unknown.
    """
    return {
        "customer_id": context.get("customer_id"),
        "root_cause": context.get("root_cause"),
        "refund_amount": context.get("refund_amount"),
        "recommended_action": context.get("recommended_action"),
        "escalated_to": "human",
    }


# --------------------------------------------------------------------------- #
# Explicit human-request detection (Task Statement 5.2)
# --------------------------------------------------------------------------- #
# Explicit phrases that mean "give me a person now." The guide says to honour an
# explicit request immediately, WITHOUT first attempting an investigation. We
# match on deliberate multi-word phrases to avoid false positives (e.g. the word
# "human" alone should not trip this).
HUMAN_REQUEST_MARKERS: tuple[str, ...] = (
    "speak to a human",
    "talk to a human",
    "speak with a human",
    "speak to a person",
    "talk to a person",
    "speak to a real person",
    "real person",
    "human agent",
    "human being",
    "human representative",
    "speak to a representative",
    "talk to a representative",
    "speak to someone",
    "talk to someone",
    "get me a human",
    "give me a human",
    "connect me to a human",
    "transfer me to a human",
    "speak to a manager",
    "talk to a manager",
    "get me a manager",
)

_WS_RE = re.compile(r"\s+")


def wants_human(message: str) -> bool:
    """Return ``True`` if the message is an explicit request for a human agent.

    Whitespace is normalised before matching so line breaks and double spaces do
    not defeat the phrase list. Matching is on explicit phrases only, so a
    passing mention of the word "human" does not trigger an escalation.
    """
    if not message:
        return False
    normalized = _WS_RE.sub(" ", message).lower()
    return any(marker in normalized for marker in HUMAN_REQUEST_MARKERS)
