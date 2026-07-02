"""Starter scaffold — error propagation across multi-agent systems (Task 5.3).

Implement the four functions below so a failing subagent hands its coordinator
*structured* context instead of a generic status, an empty "success", or a
crash. See README.md for the full brief and Sample Question 8 for the principle.

The public API here MUST match ``solution/propagation.py`` so the same tests run
against both. Replace every ``raise NotImplementedError`` with real logic.

Key semantics to get right:

* ``build_error_context`` always includes all four fields (failure_type,
  attempted, partial_results, alternatives), even when empty.
* ``classify_result`` separates an *access failure* (retry-worthy) from a valid
  *empty success* (query completed, legitimately found nothing).
* ``handle_subagent_failure`` recovers transient failures locally and propagates
  everything else UP, carrying partial results.
* ``coverage_annotations`` tags well-supported topics vs. gaps.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-20-error-propagation-provenance
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "TRANSIENT_FAILURES",
    "build_error_context",
    "classify_result",
    "handle_subagent_failure",
    "coverage_annotations",
]

# Failure types a subagent can resolve on its own by retrying. Everything else is
# permanent for a given request and must be propagated to the coordinator.
TRANSIENT_FAILURES: frozenset[str] = frozenset(
    {"timeout", "rate_limit", "service_unavailable", "connection_reset"}
)


def build_error_context(
    failure_type: str,
    attempted: Any,
    partial_results: list | None = None,
    alternatives: list | None = None,
) -> dict:
    """Build the structured error payload a subagent hands its coordinator.

    Must return a dict containing at least: ``failure_type``, ``attempted``,
    ``partial_results`` (a list, [] when none), and ``alternatives`` (a list,
    [] when none). See README.md.
    """
    # TODO: return a dict with all four fields always present.
    raise NotImplementedError


def classify_result(result: dict) -> str:
    """Return "access_failure", "empty_success", or "success" for a result.

    * "access_failure" — the query never completed (timeout/error): retry-worthy.
    * "empty_success"  — completed successfully but found nothing.
    * "success"        — completed and returned data.
    """
    # TODO: check for an error/timeout signal first; then distinguish
    # empty-but-successful from a result that actually returned data.
    raise NotImplementedError


def handle_subagent_failure(error: dict) -> dict:
    """Recover transient failures locally; propagate the rest with partial results.

    * Transient (see TRANSIENT_FAILURES) and retries not exhausted → return a
      recovered payload; the coordinator never sees it.
    * Transient but ``retries_exhausted`` → propagate structured context.
    * Non-transient (hard) failure → propagate immediately, keeping partial
      results.
    """
    # TODO: branch on failure_type / retries_exhausted; reuse build_error_context
    # when propagating.
    raise NotImplementedError


def coverage_annotations(findings: list[dict]) -> dict:
    """Annotate coverage as {"well_supported": [...], "gaps": [{...}, ...]}.

    A finding with sources and no failure marker is well-supported; one with no
    sources or a failure/gap status is a gap (record a reason).
    """
    # TODO: partition findings into well_supported topics and gaps.
    raise NotImplementedError
