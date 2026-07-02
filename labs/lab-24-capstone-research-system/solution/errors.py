"""Reference solution — structured error propagation across the research system.

Task Statement 5.3 ("Implement error propagation strategies across multi-agent
systems") and Sample Question 8.

The central rule (Sample Q8, correct answer A): when a subagent fails, return
**structured error context** — failure type, the attempted query, any partial
results, and alternative approaches — so the coordinator can make an intelligent
recovery decision (retry with a modified query, reroute, or proceed with partial
results and annotate the gap).

The anti-patterns (Sample Q8 distractors B/C/D):

- B) A generic "search unavailable" status after silent retries hides the context
  the coordinator needs.
- C) Catching the failure and returning an empty result marked *successful*
  suppresses the error — the coordinator can't tell "no matches" from "couldn't
  run" (see :func:`classify_result`).
- D) Propagating the raw exception to a top-level handler that kills the whole
  workflow throws away recoverable partial progress.

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "FAILURE_TYPES",
    "DEFAULT_TIMEOUT_ALTERNATIVES",
    "build_error_context",
    "classify_result",
    "handle_timeout",
]

# Failure types a subagent may propagate. These describe *what went wrong* so the
# coordinator can choose a strategy — unlike a uniform "failed" status.
FAILURE_TYPES = ("timeout", "access_failure", "rate_limited", "unavailable")

# Concrete recovery options the coordinator can weigh on a timeout. Passing these
# up (rather than a bare error) is what "alternative approaches" means in Q8-A.
DEFAULT_TIMEOUT_ALTERNATIVES = (
    "retry with a narrower / more specific query",
    "reroute the subtopic to the doc_analysis subagent",
    "proceed with partial results and annotate the coverage gap",
)


def build_error_context(
    failure_type: str,
    attempted_query: str,
    *,
    partial_results: list[Any] | None = None,
    alternatives: list[str] | None = None,
    subagent: str | None = None,
    facet: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Build the structured error object a subagent propagates to the coordinator.

    Includes the four things Sample Q8-A calls for: the failure type, what was
    attempted, partial results, and alternative approaches — plus which subagent
    and facet were affected so the coordinator can annotate coverage.
    """
    if not failure_type or not str(failure_type).strip():
        raise ValueError("failure_type must be a non-empty string")
    if not attempted_query or not str(attempted_query).strip():
        raise ValueError("attempted_query must be a non-empty string")
    return {
        "isError": True,
        "failure_type": failure_type,
        "attempted_query": attempted_query,
        "partial_results": list(partial_results or []),
        "alternatives": list(alternatives or []),
        "subagent": subagent,
        "facet": facet,
        "message": message
        or f"{subagent or 'subagent'} could not complete: {failure_type}",
    }


def classify_result(result: Any) -> str:
    """Distinguish an access failure from a valid empty result (Task 5.3).

    Returns one of:

    - ``"access_failure"`` — the tool could not run (an error object, an explicit
      error/timeout status, or ``None``). The coordinator may retry or reroute.
    - ``"empty_success"``  — the query ran and returned zero matches. This is a
      valid answer; do NOT retry it (retrying will fail the same way).
    - ``"results"``        — the query ran and returned one or more matches.

    Collapsing these — e.g. returning empty-as-success on a timeout — is the
    Sample Q8-C anti-pattern that prevents any recovery.
    """
    if result is None:
        return "access_failure"

    if isinstance(result, dict):
        if result.get("isError") is True or result.get("ok") is False:
            return "access_failure"
        status = str(result.get("status", "")).lower()
        if status in {"error", "failed", "failure", "unavailable", "timeout"}:
            return "access_failure"
        if result.get("failure_type"):
            return "access_failure"
        # A successful dict: look for the collection it carries.
        for key in ("findings", "results", "matches", "items", "data"):
            if key in result and isinstance(result[key], (list, tuple)):
                return "empty_success" if len(result[key]) == 0 else "results"
        return "empty_success" if len(result) == 0 else "results"

    if isinstance(result, (list, tuple)):
        return "empty_success" if len(result) == 0 else "results"

    return "results" if result else "empty_success"


def handle_timeout(
    attempted_query: str,
    *,
    partial_results: list[Any] | None = None,
    subagent: str | None = None,
    facet: str | None = None,
    alternatives: list[str] | None = None,
) -> dict[str, Any]:
    """Convert a subagent timeout into structured error context (Sample Q8-A).

    The subagent has already tried and failed locally; this packages what it
    attempted, whatever partial results it gathered, and concrete alternatives so
    the coordinator can decide how to recover — instead of the workflow dying (Q8-D)
    or the error being swallowed (Q8-C).
    """
    return build_error_context(
        "timeout",
        attempted_query,
        partial_results=partial_results,
        alternatives=list(alternatives) if alternatives is not None
        else list(DEFAULT_TIMEOUT_ALTERNATIVES),
        subagent=subagent,
        facet=facet,
        message=(
            f"{subagent or 'subagent'} timed out while researching "
            f"{facet or 'the subtopic'}; propagating partial results and "
            "alternatives for coordinator recovery."
        ),
    )
