"""Starter scaffold: Agent SDK hooks and workflow enforcement.

Implement the four programmatic-enforcement primitives from Task Statements 1.5
and 1.4. Each stub below documents the exact contract the tests expect. Replace
every ``raise NotImplementedError`` with a real implementation.

The theme of this lab is *deterministic guarantees* over *probabilistic prompt
compliance*: these rules must hold in code, on every call, regardless of how the
model was prompted.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-11-hooks-and-enforcement

This is an importable module (no shell entry point), so it needs docstrings but
is exempt from the PEP 723 / argparse script conventions.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "post_tool_use_normalize",
    "intercept_tool_call",
    "PrerequisiteGate",
    "build_handoff",
]


def post_tool_use_normalize(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    """PostToolUse hook: normalize one raw tool result into a canonical shape.

    Different tools report time and status differently. Return a NEW dict (do not
    mutate ``result``) in which:

    - ``timestamp`` (if present) becomes an ISO-8601 UTC string, whether the raw
      value was a Unix epoch int/float or an ISO-8601 string (a trailing ``Z`` or
      a naive value should be treated as UTC).
    - ``status`` (if present) becomes a human-readable label: a numeric HTTP-style
      code maps 2xx -> ``"success"``, 3xx -> ``"redirect"``, 4xx ->
      ``"client_error"``, 5xx -> ``"server_error"``; a string is lowercased.
    - a ``source_tool`` field records ``tool_name``.
    - every other field is preserved unchanged; absent fields stay absent.

    See README.md and SOLUTION.md for the full contract.
    """
    # TODO: copy result, add source_tool, normalize timestamp and status if present.
    raise NotImplementedError("Implement post_tool_use_normalize (see README.md).")


def intercept_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    refund_limit: float = 500,
) -> dict[str, Any]:
    """Interception hook: allow a tool call, or block + redirect to a human.

    If ``tool_name == "process_refund"`` and the refund amount (read from
    ``tool_input["amount"]``, falling back to ``"refund_amount"``) is strictly
    greater than ``refund_limit``, return::

        {"action": "block", "redirect": "escalate_to_human", "reason": <str>}

    Otherwise return ``{"action": "allow"}``.

    See README.md and SOLUTION.md for the full contract.
    """
    # TODO: block over-limit refunds with a redirect to escalate_to_human; else allow.
    raise NotImplementedError("Implement intercept_tool_call (see README.md).")


class PrerequisiteGate:
    """Blocks protected tools until ``get_customer`` verifies a ``customer_id``.

    Implement:

    - ``__init__(self, *, protected_tools=("process_refund", "lookup_order"),
      prerequisite_tool="get_customer")`` — store config and start with no
      verified customer id.
    - ``record_tool_result(self, name, result)`` — when ``name`` is the
      prerequisite tool AND ``result`` has a truthy ``customer_id`` AND
      ``result["verified"] is True``, remember that customer id. Otherwise do
      nothing.
    - ``check(self, tool_name) -> bool`` — return ``False`` for a protected tool
      until a verified customer id has been recorded; return ``True`` otherwise.

    See README.md and SOLUTION.md for the full contract.
    """

    def __init__(
        self,
        *,
        protected_tools: tuple[str, ...] = ("process_refund", "lookup_order"),
        prerequisite_tool: str = "get_customer",
    ) -> None:
        # TODO: store protected_tools, prerequisite_tool, and a "no verified id yet" state.
        raise NotImplementedError("Implement PrerequisiteGate.__init__ (see README.md).")

    def record_tool_result(self, name: str, result: dict[str, Any]) -> None:
        # TODO: unlock the gate on a verified prerequisite result.
        raise NotImplementedError(
            "Implement PrerequisiteGate.record_tool_result (see README.md)."
        )

    def check(self, tool_name: str) -> bool:
        # TODO: gate protected tools behind a verified customer id.
        raise NotImplementedError("Implement PrerequisiteGate.check (see README.md).")


def build_handoff(context: dict[str, Any]) -> dict[str, Any]:
    """Compile a structured escalation summary for a human agent.

    Return a dict containing ``customer_id``, ``root_cause``, ``refund_amount``,
    and ``recommended_action`` (each read from ``context``, defaulting to ``None``
    when absent), plus ``escalated_to`` set to ``"human"``.

    See README.md and SOLUTION.md for the full contract.
    """
    # TODO: pull the required fields from context and mark the handoff target.
    raise NotImplementedError("Implement build_handoff (see README.md).")
