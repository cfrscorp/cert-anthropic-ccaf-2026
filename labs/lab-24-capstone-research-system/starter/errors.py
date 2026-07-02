"""Starter — structured error propagation across the research system.

Implement the Sample Q8 behavior: when a subagent fails, propagate STRUCTURED
error context (failure type, attempted query, partial results, alternatives) so
the coordinator can recover intelligently — never a bare "search unavailable"
(Q8-B), never empty-as-success (Q8-C), never kill the whole workflow (Q8-D).

See README.md (Task C). The public API must match solution/errors.py.
This module is imported, not run as a script.
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

FAILURE_TYPES = ("timeout", "access_failure", "rate_limited", "unavailable")

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
    """Build the structured error object a subagent propagates (Sample Q8-A)."""
    # TODO: return a dict with isError, failure_type, attempted_query,
    # partial_results, alternatives, subagent, facet, message.
    raise NotImplementedError("Implement build_error_context (see README.md).")


def classify_result(result: Any) -> str:
    """Return 'access_failure', 'empty_success', or 'results' (Sample Q8-C guard)."""
    # TODO: an error object / None -> access_failure; a successful zero-length
    # result -> empty_success; otherwise -> results.
    raise NotImplementedError("Implement classify_result (see README.md).")


def handle_timeout(
    attempted_query: str,
    *,
    partial_results: list[Any] | None = None,
    subagent: str | None = None,
    facet: str | None = None,
    alternatives: list[str] | None = None,
) -> dict[str, Any]:
    """Turn a subagent timeout into structured error context (Sample Q8-A)."""
    # TODO: delegate to build_error_context with failure_type="timeout" and
    # DEFAULT_TIMEOUT_ALTERNATIVES when no alternatives are supplied.
    raise NotImplementedError("Implement handle_timeout (see README.md).")
