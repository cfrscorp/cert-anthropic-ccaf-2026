"""Starter scaffold: escalation & ambiguity resolution (Task Statement 5.2).

Implement the three functions below so a support agent can make a calibrated
three-way decision on every turn:

    * ESCALATE     — hand the case to a human now.
    * ASK_CLARIFY  — cannot act yet; gather more information.
    * RESOLVE      — handle it autonomously.

Read README.md first. The whole point of the exercise (and Sample Question 3) is
that this decision must be driven by EXPLICIT, STRUCTURAL triggers — never by
customer sentiment or the agent's self-reported confidence, which are unreliable
proxies for actual case complexity.

These are pure functions — no Claude client is needed.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "decide",
    "uses_unreliable_signal",
    "build_escalation_criteria",
]


def decide(context: dict[str, Any]) -> str:
    """Return one of ``"ESCALATE"``, ``"ASK_CLARIFY"``, ``"RESOLVE"``.

    See README.md for the full context schema. Recognized context keys include
    ``explicit_human_request``, ``reiterated_human_request``,
    ``customer_matches``, ``policy_status`` ("covered"/"gap"/"silent"/
    "ambiguous"), ``can_make_progress``, ``within_capability``, and
    ``straightforward``. The keys ``sentiment`` and ``self_reported_confidence``
    may be present but MUST NOT influence the decision.

    Apply the checks in priority order:
        1. Explicit (or reiterated) human request -> ESCALATE immediately.
        2. Multiple customer matches -> ASK_CLARIFY.
        3. Policy gap / silent / ambiguous -> ESCALATE.
        4. Cannot make meaningful progress -> ESCALATE.
        5. Outside the agent's capability -> ESCALATE.
        6. Straightforward and within capability -> RESOLVE.
        7. Otherwise -> ESCALATE (safe default).
    """
    # TODO: implement the priority-ordered checks above.
    # TODO: do NOT branch on context["sentiment"] or
    #       context["self_reported_confidence"].
    raise NotImplementedError("Implement decide (see README.md and the TODOs).")


def uses_unreliable_signal(policy: dict[str, Any]) -> bool:
    """Return ``True`` if a decision *policy* relies on sentiment/confidence.

    ``policy`` is a dict describing how decisions are made, e.g.
    ``{"name": "...", "signals": ["policy_status", "customer_matches"]}``.
    Recursively inspect its keys and string values and return ``True`` if any
    references an unreliable signal (substrings such as "sentiment",
    "confidence", "frustration", "mood", "tone").
    """
    # TODO: collect all string tokens from the policy (keys + string values,
    #       recursively) and check for unreliable-signal substrings.
    raise NotImplementedError(
        "Implement uses_unreliable_signal (see README.md and the TODOs)."
    )


def build_escalation_criteria(examples: list[dict[str, str]]) -> str:
    """Build a system-prompt snippet: explicit criteria + few-shot examples.

    ``examples`` is a list of dicts with ``"situation"``, ``"decision"``, and
    optionally ``"reason"`` keys. Return a prompt-ready string that (a) states
    the explicit escalation criteria and (b) embeds every example verbatim so the
    model can pattern-match. Raise ``ValueError`` if ``examples`` is empty.
    """
    # TODO: build the criteria section, then append each example's situation,
    #       decision, and reason so they appear verbatim in the output.
    raise NotImplementedError(
        "Implement build_escalation_criteria (see README.md and the TODOs)."
    )
