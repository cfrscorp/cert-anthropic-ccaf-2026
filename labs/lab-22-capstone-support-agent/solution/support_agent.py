"""Capstone reference — the customer-support resolution agent.

This module ties every earlier lab together into one realistic agent
(Scenario 1 / Preparation Exercise 1). :func:`run_support_agent` drives a
model-driven agentic loop and layers the programmatic guardrails on top:

1. **Agentic loop (Task Statement 1.1).** Termination is decided ONLY by
   ``stop_reason`` — ``"tool_use"`` continues, anything else ends. We never parse
   the assistant's prose to decide when to stop and never use an iteration count
   as the primary stopping mechanism.
2. **Prerequisite gate (1.4 / SQ1).** ``lookup_order`` and ``process_refund`` are
   refused until ``get_customer`` verifies the customer — in code, deterministically.
3. **Refund interception (1.5).** A refund over the ceiling is blocked and
   redirected to human escalation with a structured handoff.
4. **Structured tool errors (2.2).** A *transient* tool error is retried locally;
   a *business* error is fed back so the model explains it to the customer.
5. **Escalation & ambiguity (5.2).** An explicit human request escalates
   immediately without any investigation; multiple customer matches trigger a
   clarification request instead of a heuristic guess.
6. **Multi-concern decomposition (1.4).** A message with several issues is split
   into distinct concerns investigated under one shared context.
7. **Persistent case-facts block (5.1).** Amounts, dates, order numbers and
   statuses are extracted verbatim from the message and every tool result into a
   compact block that is re-injected into the system prompt each turn — so the
   values a progressive summary would blur ("about $130") survive intact.

The Claude client is dependency-injected (any object with
``client.messages.create(...)`` — the real SDK or the lab's ``MockAnthropic``).

Self-contained: imports only its sibling modules ``tools`` and ``guardrails``.
Imported module — docstrings required, exempt from the script conventions.
"""

from __future__ import annotations

import json
import re
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

# --------------------------------------------------------------------------- #
# Case-facts extraction (Task Statement 5.1)
# --------------------------------------------------------------------------- #
_AMOUNT_RE = re.compile(r"\$\d[\d,]*(?:\.\d{2})?")
_DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b")
_ORDER_RE = re.compile(r"\bORD-\d{3,}\b")
_STATUS_TERMS = (
    "out for delivery",
    "in transit",
    "backordered",
    "processing",
    "delivered",
    "shipped",
    "cancelled",
    "canceled",
    "refunded",
    "returned",
    "pending",
)


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _as_text(item: Any) -> str:
    """Best-effort text for a fact source (string, dict, or content blocks)."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        content = item.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [str(b.get("text", "")) for b in content if isinstance(b, dict)]
            return " ".join(parts) or json.dumps(item, default=str)
        return json.dumps(item, default=str)
    return str(item)


def extract_case_facts(sources: list[Any]) -> dict[str, list[str]]:
    """Extract transactional facts into a persistent case-facts block.

    Scans each source (the customer message and every tool result) and pulls out
    the values a progressive summary is most likely to lose: dollar amounts,
    dates, order numbers, and statuses. Values are returned verbatim,
    de-duplicated, in first-seen order.

    Returns a dict with keys ``amounts``, ``dates``, ``order_numbers`` and
    ``statuses``.
    """
    amounts: list[str] = []
    dates: list[str] = []
    orders: list[str] = []
    statuses: list[str] = []
    for source in sources:
        text = _as_text(source)
        if not text:
            continue
        amounts.extend(_AMOUNT_RE.findall(text))
        dates.extend(_DATE_RE.findall(text))
        orders.extend(_ORDER_RE.findall(text))
        lowered = text.lower()
        for term in _STATUS_TERMS:
            if term in lowered:
                statuses.append(term)
    return {
        "amounts": _dedupe(amounts),
        "dates": _dedupe(dates),
        "order_numbers": _dedupe(orders),
        "statuses": _dedupe(statuses),
    }


# --------------------------------------------------------------------------- #
# Multi-concern decomposition (Task Statement 1.4)
# --------------------------------------------------------------------------- #
# Split on sentence boundaries and on additive connectives ("also", "additionally",
# "second", "plus") that typically introduce a second, distinct concern.
_CONCERN_SPLIT_RE = re.compile(
    r"(?<=[.?!])\s+|\s*(?:;|\band also\b|\balso\b|\badditionally\b|\bsecond(?:ly)?\b|\bplus\b)\s*",
    flags=re.IGNORECASE,
)


def decompose_concerns(message: str) -> list[str]:
    """Split a multi-concern message into distinct concern strings.

    A single-issue message returns one concern; a message raising several issues
    ("Where is my order? Also, I need a refund…") returns one entry per issue so
    each can be investigated under the shared case context before a single unified
    reply is synthesized.
    """
    if not message or not message.strip():
        return []
    parts = _CONCERN_SPLIT_RE.split(message)
    concerns = [p.strip(" ,.;") for p in parts if p and len(p.strip(" ,.;")) > 3]
    return concerns or [message.strip()]


# --------------------------------------------------------------------------- #
# System prompt: escalation criteria + few-shot + live case-facts (5.1/5.2)
# --------------------------------------------------------------------------- #
ESCALATION_EXAMPLES: list[dict[str, str]] = [
    {
        "situation": "Customer says 'just get me a human, now.'",
        "decision": "ESCALATE immediately",
        "reason": "Honour an explicit request for a human without investigating first.",
    },
    {
        "situation": "Standard damaged-item replacement with photo evidence, $40.",
        "decision": "RESOLVE",
        "reason": "Straightforward and within capability; do not escalate a routine case.",
    },
    {
        "situation": "Customer wants a competitor price match; policy only covers own-site adjustments.",
        "decision": "ESCALATE",
        "reason": "Policy is silent on this request — a policy gap, not merely a hard case.",
    },
    {
        "situation": "A name lookup returns two accounts.",
        "decision": "ASK for the customer_id",
        "reason": "Multiple matches require a clarifying identifier, never a heuristic pick.",
    },
]


def build_system_prompt(case_facts: dict[str, list[str]], *, refund_limit: float) -> str:
    """Build the system prompt: role, ordering rules, escalation criteria, facts.

    The case-facts block is injected here (outside the summarized turn history)
    and rebuilt every turn so transactional values persist verbatim across a long
    conversation (Task Statement 5.1).
    """
    lines = [
        "You are a customer-support resolution agent. Target 80%+ first-contact",
        "resolution while knowing when to escalate.",
        "",
        "Tool ordering: call get_customer to VERIFY the customer before any",
        "lookup_order or process_refund. (This is also enforced in code.)",
        f"Refunds are auto-approved only up to ${refund_limit}; larger refunds are",
        "blocked and must go to human escalation.",
        "",
        "Escalation & ambiguity rules:",
        "1. If the customer explicitly asks for a human, escalate immediately —",
        "   do not investigate first.",
        "2. If more than one customer record matches, ask for an additional",
        "   identifier; never pick a match by heuristic.",
        "3. If policy is silent/ambiguous on the request, escalate (policy gap).",
        "4. If you cannot make meaningful progress, escalate.",
        "5. Otherwise, if it is straightforward and within capability, resolve.",
        "Do NOT base the decision on customer sentiment or your own confidence.",
        "",
        "Worked examples:",
    ]
    for i, ex in enumerate(ESCALATION_EXAMPLES, start=1):
        lines.append(f"{i}. {ex['situation']} -> {ex['decision']} ({ex['reason']})")
    lines += [
        "",
        "Case facts (verbatim — preserve these values exactly):",
        json.dumps(case_facts, indent=2),
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The agent
# --------------------------------------------------------------------------- #
def _tool_result_block(tool_use_id: str, content: Any) -> dict[str, Any]:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}


def _first_amount(case_facts: dict[str, list[str]]) -> str | None:
    amounts = case_facts.get("amounts") or []
    return amounts[0] if amounts else None


def _execute_with_retry(
    name: str, tool_input: dict, backends: dict, max_tool_retries: int
) -> tuple[dict[str, Any], int]:
    """Execute a tool, retrying locally only on retryable (transient) errors.

    A business/validation/permission error is returned on the first attempt (not
    retried), so the agent communicates instead of wasting attempts. Returns the
    final result and the number of attempts made.
    """
    attempts = 0
    result: dict[str, Any] = {}
    for _ in range(max_tool_retries + 1):
        attempts += 1
        result = execute_tool(name, tool_input, backends)
        retryable = isinstance(result, dict) and result.get("isError") and result.get("isRetryable")
        if not retryable:
            break
    return result, attempts


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

    Args:
        client: Anthropic-style client (real SDK or ``MockAnthropic``).
        message: The customer's opening message.
        backends: Tool backends (data and/or callable overrides). Defaults to
            :func:`tools.default_backends`.
        model, max_tokens: Passed through to each model call.
        refund_limit: Auto-approval ceiling for the interception hook.
        max_tool_retries: Extra local retries for a *transient* tool error.
        safety_cap: Backstop against a runaway loop (NOT the normal stop signal).

    Returns:
        A dict with: ``final_text``, ``iterations``, ``messages``, ``case_facts``,
        ``concerns``, ``tool_calls``, ``escalated``, ``escalation_reason``,
        ``handoff``, ``clarification_requested`` and ``verified_customer_id``.
    """
    if backends is None:
        backends = default_backends()

    concerns = decompose_concerns(message)
    fact_sources: list[Any] = [message]
    case_facts = extract_case_facts(fact_sources)

    # --- Escalation pre-check: honour an explicit human request immediately. ---
    # Task Statement 5.2: escalate without first attempting any investigation. We
    # short-circuit before calling the model at all, so no order/customer tools run.
    if wants_human(message):
        handoff = build_handoff({
            "customer_id": None,
            "root_cause": "Customer explicitly requested a human agent.",
            "refund_amount": _first_amount(case_facts),
            "recommended_action": "Connect the customer to a human support agent.",
        })
        return {
            "final_text": (
                "Of course — I'm connecting you with a human support agent right now. "
                "They'll have the details of your request."
            ),
            "iterations": 0,
            "messages": [{"role": "user", "content": message}],
            "case_facts": case_facts,
            "concerns": concerns,
            "tool_calls": [],
            "escalated": True,
            "escalation_reason": "explicit_human_request",
            "handoff": handoff,
            "clarification_requested": False,
            "verified_customer_id": None,
        }

    # --- Agentic loop. ---
    gate = PrerequisiteGate()
    messages: list[dict[str, Any]] = [{"role": "user", "content": message}]
    tool_calls: list[dict[str, Any]] = []
    escalated = False
    escalation_reason: str | None = None
    handoff: dict[str, Any] | None = None
    clarification_requested = False
    iterations = 0
    final_text = ""

    while True:
        if iterations >= safety_cap:
            raise RuntimeError(
                f"safety_cap of {safety_cap} model calls exceeded without an "
                "end_turn; the loop is not making progress."
            )

        # Rebuild the system prompt each turn so the (growing) case-facts block is
        # re-injected outside the summarized history.
        system = build_system_prompt(case_facts, refund_limit=refund_limit)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=TOOLS,
        )
        iterations += 1
        messages.append({"role": "assistant", "content": resp.content})

        # The ONLY termination signal is stop_reason (Task Statement 1.1).
        if resp.stop_reason != "tool_use":
            final_text = resp.text
            break

        tool_results: list[dict[str, Any]] = []
        for block in resp.tool_use_blocks():
            name = block.name
            tool_input = block.input or {}

            # 1. Interception hook: block an over-limit refund and escalate.
            decision = intercept_tool_call(name, tool_input, refund_limit=refund_limit)
            if decision.get("action") == "block":
                escalated = True
                escalation_reason = "refund_over_limit"
                handoff = build_handoff({
                    "customer_id": gate.verified_customer_id,
                    "root_cause": decision["reason"],
                    "refund_amount": tool_input.get("amount", tool_input.get("refund_amount")),
                    "recommended_action": "Human review required for an over-limit refund.",
                })
                result = {
                    "isError": True,
                    "errorCategory": "business",
                    "isRetryable": False,
                    "redirected": "escalate_to_human",
                    "message": decision["reason"],
                }
                tool_calls.append({"name": name, "input": tool_input, "blocked": True,
                                   "reason": "refund_over_limit", "attempts": 0, "result": result})
                tool_results.append(_tool_result_block(block.id, json.dumps(result)))
                continue

            # 2. Prerequisite gate: refuse account ops before identity is verified.
            if not gate.check(name):
                result = {
                    "isError": True,
                    "errorCategory": "validation",
                    "isRetryable": False,
                    "message": (
                        f"'{name}' is blocked until get_customer has verified the "
                        "customer. Call get_customer first."
                    ),
                }
                tool_calls.append({"name": name, "input": tool_input, "blocked": True,
                                   "reason": "prerequisite", "attempts": 0, "result": result})
                tool_results.append(_tool_result_block(block.id, json.dumps(result)))
                continue

            # 3. Execute (with local retry only for transient errors).
            result, attempts = _execute_with_retry(name, tool_input, backends, max_tool_retries)
            gate.record_tool_result(name, result)

            if name == "get_customer" and result.get("match_count", 1) > 1:
                clarification_requested = True
            if name == "escalate_to_human":
                escalated = True
                escalation_reason = escalation_reason or "agent_escalation"
                handoff = build_handoff({
                    "customer_id": tool_input.get("customer_id", gate.verified_customer_id),
                    "root_cause": tool_input.get("root_cause"),
                    "refund_amount": tool_input.get("refund_amount"),
                    "recommended_action": tool_input.get("recommended_action"),
                })

            tool_calls.append({"name": name, "input": tool_input, "blocked": False,
                               "attempts": attempts, "result": result})

            # Refresh the persistent case-facts block from the new tool result.
            fact_sources.append(result)
            case_facts = extract_case_facts(fact_sources)

            tool_results.append(_tool_result_block(block.id, json.dumps(result)))

        messages.append({"role": "user", "content": tool_results})

    return {
        "final_text": final_text,
        "iterations": iterations,
        "messages": messages,
        "case_facts": case_facts,
        "concerns": concerns,
        "tool_calls": tool_calls,
        "escalated": escalated,
        "escalation_reason": escalation_reason,
        "handoff": handoff,
        "clarification_requested": clarification_requested,
        "verified_customer_id": gate.verified_customer_id,
    }
