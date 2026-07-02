"""Capstone starter — the programmatic-enforcement layer.

Implement the deterministic guardrails that wrap the agentic loop. Keep the
public API identical to the reference solution.

Public API you must provide:
    REFUND_LIMIT, HUMAN_REQUEST_MARKERS
    class PrerequisiteGate: check(name) / record_tool_result(name, result) / verified_customer_id
    intercept_tool_call(tool_name, tool_input, *, refund_limit=REFUND_LIMIT) -> dict
    build_handoff(context) -> dict
    wants_human(message) -> bool
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "REFUND_LIMIT",
    "PrerequisiteGate",
    "intercept_tool_call",
    "build_handoff",
    "wants_human",
    "HUMAN_REQUEST_MARKERS",
]

REFUND_LIMIT: float = 500

# TODO: list explicit multi-word phrases that mean "give me a person now" (avoid
# matching a bare "human" to prevent false positives). See Task Statement 5.2.
HUMAN_REQUEST_MARKERS: tuple[str, ...] = ()


class PrerequisiteGate:
    """Block lookup_order / process_refund until get_customer verifies identity.

    The programmatic answer to Sample Question 1: a gate, not a stronger prompt.
    Only a get_customer result with a truthy customer_id AND verified is True
    unlocks the gate.
    """

    def __init__(
        self,
        *,
        protected_tools: tuple[str, ...] = ("lookup_order", "process_refund"),
        prerequisite_tool: str = "get_customer",
    ) -> None:
        raise NotImplementedError("Implement PrerequisiteGate (Task Statement 1.4 / SQ1).")

    @property
    def verified_customer_id(self) -> str | None:
        raise NotImplementedError

    def record_tool_result(self, name: str, result: dict[str, Any]) -> None:
        raise NotImplementedError

    def check(self, tool_name: str) -> bool:
        raise NotImplementedError


def intercept_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    refund_limit: float = REFUND_LIMIT,
) -> dict[str, Any]:
    """Allow a call, or block an over-limit process_refund and redirect to human.

    Return ``{"action": "allow"}`` or
    ``{"action": "block", "redirect": "escalate_to_human", "reason": ...}``.
    """
    raise NotImplementedError("Implement intercept_tool_call (Task Statement 1.5).")


def build_handoff(context: dict[str, Any]) -> dict[str, Any]:
    """Return customer_id, root_cause, refund_amount, recommended_action (default
    None) plus escalated_to='human' (Task Statement 1.4)."""
    raise NotImplementedError("Implement build_handoff (Task Statement 1.4).")


def wants_human(message: str) -> bool:
    """Return True if the message is an explicit request for a human agent."""
    raise NotImplementedError("Implement wants_human (Task Statement 5.2).")
