"""Capstone starter — the customer-support resolution agent.

Wire the earlier labs together into one agent (Scenario 1 / Exercise 1).
Implement :func:`run_support_agent` as a model-driven agentic loop and layer the
guardrails from ``guardrails.py`` and the tools from ``tools.py`` on top. Keep
the public API identical to the reference solution.

Public API you must provide:
    run_support_agent(client, message, backends=None, *, ...) -> dict
    extract_case_facts(sources) -> dict
    decompose_concerns(message) -> list[str]
    build_system_prompt(case_facts, *, refund_limit) -> str
    ESCALATION_EXAMPLES

The returned dict must include at least: final_text, iterations, messages,
case_facts, concerns, tool_calls, escalated, escalation_reason, handoff,
clarification_requested, verified_customer_id.
"""

from __future__ import annotations

from typing import Any

from guardrails import PrerequisiteGate, build_handoff, intercept_tool_call, wants_human
from tools import TOOLS, execute_tool, default_backends

__all__ = [
    "run_support_agent",
    "extract_case_facts",
    "decompose_concerns",
    "build_system_prompt",
    "ESCALATION_EXAMPLES",
]

# TODO: 3-4 few-shot escalation examples (situation / decision / reason) that
# distinguish escalate vs resolve vs ask-for-identifier (Task Statement 5.2).
ESCALATION_EXAMPLES: list[dict[str, str]] = []


def extract_case_facts(sources: list[Any]) -> dict[str, list[str]]:
    """Extract amounts/dates/order_numbers/statuses verbatim into a facts block
    (Task Statement 5.1). Scan the message and every tool result."""
    raise NotImplementedError("Implement extract_case_facts (Task Statement 5.1).")


def decompose_concerns(message: str) -> list[str]:
    """Split a multi-concern message into distinct concerns (Task Statement 1.4)."""
    raise NotImplementedError("Implement decompose_concerns (Task Statement 1.4).")


def build_system_prompt(case_facts: dict[str, list[str]], *, refund_limit: float) -> str:
    """Build the system prompt: role, ordering rules, escalation criteria +
    few-shot, and the live case-facts block (Task Statements 5.1/5.2)."""
    raise NotImplementedError("Implement build_system_prompt.")


def run_support_agent(
    client: Any,
    message: str,
    backends: dict[str, Any] | None = None,
    *,
    model: str = "claude-mock",
    max_tokens: int = 1024,
    refund_limit: float = 500,
    max_tool_retries: int = 2,
    safety_cap: int = 25,
) -> dict[str, Any]:
    """Run the support agent on one customer ``message``.

    Implement the agentic loop (terminate ONLY on stop_reason), the prerequisite
    gate, the refund interception hook, structured-error retry/explain handling,
    the explicit-human-request short-circuit, multiple-match clarification, and
    multi-concern decomposition with a persistent case-facts block.
    """
    raise NotImplementedError("Implement run_support_agent (the capstone integration).")
