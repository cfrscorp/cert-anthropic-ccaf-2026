"""Reference implementation: escalation & ambiguity resolution (Task Statement 5.2).

A support agent constantly faces the same three-way decision on every turn:

    * ESCALATE     — hand the case to a human now.
    * ASK_CLARIFY  — the agent cannot act yet and must gather more information.
    * RESOLVE      — the agent can and should handle this autonomously.

The *hard* part is calibration: the guide (5.2) is emphatic that this decision
must be driven by **explicit, structural triggers**, not by proxies that feel
predictive but are not:

    * an explicit customer request for a human  -> ESCALATE immediately, with no
      prior investigation (honor the request);
    * policy that is silent / ambiguous / has a gap on the specific request
      -> ESCALATE (a policy *gap*, not merely a "complex" case);
    * inability to make meaningful progress (e.g. backend down) -> ESCALATE;
    * multiple customer records match the identifiers -> ASK_CLARIFY for another
      identifier, rather than picking one by a heuristic;
    * straightforward and within the agent's capability -> RESOLVE.

Crucially, **sentiment** ("the customer sounds furious") and **self-reported
confidence** ("I'm 95% sure") are UNRELIABLE proxies for case complexity and are
never branched on. A frustrated customer with a routine request should still be
helped; a cheerful request that needs a policy exception should still escalate.
This is exactly the failure mode in Sample Question 3, where the fix is explicit
criteria + few-shot examples, not sentiment analysis (D) or a confidence
threshold (B).

Pure decision logic — no Claude client is needed, so the functions are directly
unit-testable and deterministic.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "decide",
    "uses_unreliable_signal",
    "build_escalation_criteria",
    "UNRELIABLE_SIGNAL_ROOTS",
    "POLICY_GAP_STATES",
]

# Substrings that identify an unreliable escalation signal. If a decision policy
# branches on any of these, it is calibrating on a proxy the guide warns against.
UNRELIABLE_SIGNAL_ROOTS: tuple[str, ...] = (
    "sentiment",
    "confidence",
    "frustration",
    "mood",
    "tone",
    "anger",
    "emotion",
)

# Policy states that mean the written policy does not cleanly cover the request.
POLICY_GAP_STATES: frozenset[str] = frozenset({"gap", "silent", "ambiguous"})


def decide(context: dict[str, Any]) -> str:
    """Return the escalation decision for a single case: one of the three actions.

    Args:
        context: A description of the case. Recognized keys (all optional, with
            safe defaults):
              - ``explicit_human_request`` (bool): the customer directly asked for
                a human on this turn. Default ``False``.
              - ``reiterated_human_request`` (bool): the customer repeated a
                request for a human after being offered a resolution. Treated the
                same as an explicit request. Default ``False``.
              - ``customer_matches`` (int): how many customer records match the
                supplied identifiers. Default ``1``.
              - ``policy_status`` (str): one of ``"covered"``, ``"gap"``,
                ``"silent"``, ``"ambiguous"``. Default ``"covered"``.
              - ``can_make_progress`` (bool): whether the agent can make
                meaningful progress (tools reachable, data available). Default
                ``True``.
              - ``within_capability`` (bool): whether the action is something the
                agent is permitted/able to do. Default ``True``.
              - ``straightforward`` (bool): whether the request is routine given
                the above. Default ``True``.
            ``sentiment`` and ``self_reported_confidence`` may be present but are
            deliberately IGNORED — they are unreliable proxies for complexity.

    Returns:
        ``"ESCALATE"``, ``"ASK_CLARIFY"``, or ``"RESOLVE"``.

    The ordering of the checks encodes the priority the guide describes:

        1. Honor an explicit (or reiterated) human request *immediately* — before
           any investigation. This is first so nothing else can pre-empt it.
        2. If identity is ambiguous (multiple matches), we cannot safely act on
           anyone's account yet -> ASK_CLARIFY for another identifier.
        3. If policy is silent/ambiguous/has a gap on the request -> ESCALATE.
        4. If we cannot make meaningful progress -> ESCALATE.
        5. If the action is outside the agent's capability -> ESCALATE.
        6. If it is straightforward and within capability -> RESOLVE.
        7. Anything left over is, by definition, not clearly resolvable ->
           ESCALATE (the safe default).
    """
    # 1. Explicit customer demand for a human wins over everything, with no prior
    #    investigation. Note we do NOT look at sentiment/confidence here or below.
    if context.get("explicit_human_request") or context.get("reiterated_human_request"):
        return "ESCALATE"

    # 2. Multiple records match -> ask for another identifier rather than guessing
    #    via a heuristic (e.g. "pick the most recent order").
    if int(context.get("customer_matches", 1)) > 1:
        return "ASK_CLARIFY"

    # 3. Policy gap / silence / ambiguity on the specific request -> escalate.
    if context.get("policy_status", "covered") in POLICY_GAP_STATES:
        return "ESCALATE"

    # 4. Cannot make meaningful progress (e.g. backend outage, missing data).
    if not context.get("can_make_progress", True):
        return "ESCALATE"

    # 5. Action is outside what the agent is allowed / able to do.
    if not context.get("within_capability", True):
        return "ESCALATE"

    # 6. Routine and within capability -> handle it (regardless of tone/mood).
    if context.get("straightforward", True):
        return "RESOLVE"

    # 7. Not clearly resolvable -> escalate rather than guess.
    return "ESCALATE"


def uses_unreliable_signal(policy: dict[str, Any]) -> bool:
    """Return ``True`` if a decision *policy* relies on sentiment/confidence.

    This is a lint over a policy specification, not over a single case. A policy
    is any dict that describes how escalation decisions are made — e.g.::

        {"name": "...", "signals": ["policy_status", "customer_matches"]}

    We recursively collect every string token (keys and string values) and flag
    the policy if any token contains an unreliable-signal root such as
    ``"sentiment"`` or ``"confidence"`` (see :data:`UNRELIABLE_SIGNAL_ROOTS`).
    Branching on these is the anti-pattern behind Sample Question 3 options B and
    D: sentiment does not correlate with complexity, and self-reported confidence
    is poorly calibrated on exactly the hard cases.

    Args:
        policy: A policy specification dict.

    Returns:
        ``True`` if any unreliable signal is referenced, else ``False``.
    """
    tokens = _collect_tokens(policy)
    return any(
        root in token
        for token in tokens
        for root in UNRELIABLE_SIGNAL_ROOTS
    )


def _collect_tokens(obj: Any) -> list[str]:
    """Recursively gather all lowercased string tokens (keys and values)."""
    tokens: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                tokens.append(key.lower())
            tokens.extend(_collect_tokens(value))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            tokens.extend(_collect_tokens(item))
    elif isinstance(obj, str):
        tokens.append(obj.lower())
    return tokens


def build_escalation_criteria(examples: list[dict[str, str]]) -> str:
    """Build a system-prompt snippet: explicit criteria + few-shot examples.

    This is the concrete remedy from Sample Question 3 / Task Statement 5.2:
    give the agent *explicit* escalation criteria and back them with a handful of
    few-shot examples that show the decision AND the reasoning for choosing it
    over the plausible alternative. That closes the fuzzy decision boundary far
    more cheaply and reliably than a trained classifier or a sentiment threshold.

    Args:
        examples: A list of dicts, each with ``"situation"``, ``"decision"``,
            and (optionally) ``"reason"`` keys. Every example is embedded
            verbatim in the returned snippet so the model can pattern-match.

    Returns:
        A prompt-ready string with a criteria section and a worked-examples
        section.

    Raises:
        ValueError: if ``examples`` is empty (few-shot needs shots).
    """
    if not examples:
        raise ValueError("Provide at least one few-shot example.")

    lines: list[str] = [
        "## Escalation & ambiguity policy",
        "",
        "Decide exactly ONE of: ESCALATE, ASK_CLARIFY, RESOLVE.",
        "",
        "Apply these criteria in order:",
        "1. If the customer explicitly asks for a human, ESCALATE immediately —"
        " do not investigate first.",
        "2. If more than one customer record matches, ASK_CLARIFY: request an"
        " additional identifier. Never pick a match by heuristic.",
        "3. If policy is silent, ambiguous, or has a gap for this specific"
        " request, ESCALATE (e.g. competitor price-matching when policy only"
        " covers own-site adjustments).",
        "4. If you cannot make meaningful progress (outage, missing data),"
        " ESCALATE.",
        "5. Otherwise, if it is straightforward and within your capability,"
        " RESOLVE.",
        "",
        "Do NOT base the decision on customer sentiment or on your own confidence"
        " score — neither reliably indicates case complexity. Acknowledge"
        " frustration and still offer a resolution when the request is within"
        " your capability; escalate only if the customer reiterates the request"
        " for a human.",
        "",
        "### Examples",
    ]

    for i, example in enumerate(examples, start=1):
        situation = example.get("situation", "")
        decision = example.get("decision", "")
        reason = example.get("reason", "")
        lines.append(f"{i}. Situation: {situation}")
        lines.append(f"   Decision: {decision}")
        if reason:
            lines.append(f"   Why (not the alternative): {reason}")

    return "\n".join(lines)
