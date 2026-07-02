"""Reference solution — error propagation across multi-agent systems (Task 5.3).

A subagent that fails must not collapse the whole workflow, and it must not lie
about what happened. Two anti-patterns (see Sample Question 8) are equally wrong:

* **Suppress-as-success** — catch the failure and return an empty result marked
  "successful". The coordinator can never recover because it never learns there
  was anything to recover from, and the final report is silently incomplete.
* **Terminate-all** — let one subagent's timeout crash the entire research run,
  even though the coordinator could have retried, tried an alternative source, or
  proceeded with partial results.

The correct approach is **structured error context**: the failing subagent hands
the coordinator the failure type, the query it attempted, whatever partial
results it did gather, and alternative approaches worth trying. With that, the
coordinator can make an *intelligent* recovery decision instead of guessing from
a generic "search unavailable" string.

This module models that contract offline:

* ``build_error_context`` — the four-field structured payload.
* ``classify_result``     — access failure (retry-worthy) vs. valid empty result.
* ``handle_subagent_failure`` — recover transient failures locally; propagate the
  rest UP with partial results attached.
* ``coverage_annotations`` — tag which synthesis topics are well-supported and
  which are gaps due to unavailable sources.

Imported by the test suite; not a shell script, so the PEP 723 / argparse
conventions do not apply (docstrings instead).
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

# Failure types that a subagent can reasonably resolve on its own by retrying:
# they are typically momentary. Everything else (auth, not-found, malformed
# query) will fail identically on retry and must be propagated to the coordinator.
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

    All four fields the coordinator needs to make a recovery decision are always
    present — even when empty — so downstream code never has to guess whether a
    key is missing or genuinely absent:

    * ``failure_type``   — what went wrong (e.g. "timeout"), not a generic status.
    * ``attempted``      — the exact query/operation that failed, so a retry can
      be modified rather than blindly repeated.
    * ``partial_results``— anything gathered before the failure; never discarded.
    * ``alternatives``   — other approaches the coordinator could try.
    """
    return {
        "status": "error",
        "failure_type": failure_type,
        "attempted": attempted,
        "partial_results": list(partial_results) if partial_results else [],
        "alternatives": list(alternatives) if alternatives else [],
    }


def classify_result(result: dict) -> str:
    """Classify a subagent result so the coordinator reacts appropriately.

    Returns one of:

    * ``"access_failure"`` — the query never completed (timeout, error, refusal).
      This is *retry-worthy*: the answer is unknown, not "nothing found".
    * ``"empty_success"``  — the query completed successfully and legitimately
      found nothing. Retrying is pointless; the emptiness is the real answer.
    * ``"success"``        — the query completed and returned data.

    Conflating the first two is the ``5.3`` trap: an empty *access failure*
    silently becomes "no results", and the coordinator proceeds on a false
    assumption. The signals are kept explicit so they cannot be confused.
    """
    # Any explicit error signal => the query did not complete => access failure.
    if (
        result.get("status") == "error"
        or result.get("error")
        or result.get("isError")
        or result.get("failure_type")
        or result.get("timed_out")
    ):
        return "access_failure"

    # Otherwise the query completed. Distinguish "found nothing" from "found data"
    # by the presence of results, not by the truthiness of the whole payload.
    results = result.get("results", result.get("data", []))
    if not results:
        return "empty_success"
    return "success"


def handle_subagent_failure(error: dict) -> dict:
    """Decide whether to recover locally or propagate a subagent failure.

    Policy (Task 5.3): a subagent implements **local recovery for transient
    failures** and only **propagates errors it cannot resolve** — always carrying
    what was attempted and any partial results.

    * Transient failure with local retries left → recover *in place*. The
      coordinator never sees it; the recovered payload (``recovery_result``, if
      any) is returned as a normal success.
    * Transient failure whose retries are exhausted → propagate structured
      context (the retry budget is spent; the coordinator must decide).
    * Any non-transient (hard) failure → propagate immediately with partial
      results, since retrying would fail identically.
    """
    failure_type = error.get("failure_type", "unknown")
    attempted = error.get("attempted")
    partial = error.get("partial_results", [])
    alternatives = error.get("alternatives", [])

    is_transient = failure_type in TRANSIENT_FAILURES
    retries_exhausted = bool(error.get("retries_exhausted"))

    if is_transient and not retries_exhausted:
        # Local recovery: retry resolved (or would resolve) the momentary blip.
        return {
            "status": "recovered",
            "recovered_locally": True,
            "failure_type": failure_type,
            "result": error.get("recovery_result", []),
        }

    # Propagate UP: hard failure, or a transient one we could not resolve locally.
    ctx = build_error_context(failure_type, attempted, partial, alternatives)
    ctx["recovered_locally"] = False
    return ctx


def coverage_annotations(findings: list[dict]) -> dict:
    """Annotate synthesis coverage: well-supported topics vs. gaps.

    Structuring synthesis output with coverage annotations (Task 5.3) tells the
    reader which conclusions rest on real sources and which topic areas are
    missing because a source was unavailable — so a gap is never mistaken for
    "we looked and there's nothing there".

    Each finding is a dict with a ``topic`` and either sources (well-supported)
    or a failure marker / no sources (a gap). Returns::

        {"well_supported": [topic, ...],
         "gaps": [{"topic": ..., "reason": ...}, ...]}
    """
    well_supported: list = []
    gaps: list[dict] = []
    for finding in findings:
        topic = finding.get("topic", "unknown")
        sources = finding.get("sources", [])
        failed = bool(finding.get("error")) or finding.get("status") in (
            "gap",
            "error",
            "access_failure",
        )
        if sources and not failed:
            well_supported.append(topic)
        else:
            gaps.append(
                {
                    "topic": topic,
                    "reason": finding.get("reason")
                    or finding.get("failure_type")
                    or "no sources available",
                }
            )
    return {"well_supported": well_supported, "gaps": gaps}
