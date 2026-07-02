"""Starter — synthesis with provenance, conflict handling, and verify_fact.

Implement the Task 5.6 provenance rules and the Sample Q9 scoped-tool pattern.
See README.md (Task D). The public API must match solution/synthesis.py.
This module is imported, not run as a script.
"""

from __future__ import annotations

from typing import Any, Callable

from agents import verify_fact_schema  # noqa: F401  (used by verify())

__all__ = [
    "merge_claims",
    "annotate_conflict",
    "coverage_annotations",
    "render_by_type",
    "classify_verification",
    "verify",
    "synthesize",
]


def merge_claims(finding_lists: Any) -> list[dict[str, Any]]:
    """Flatten per-subagent findings, preserving each claim's source (Task 5.6)."""
    # TODO: accept a list-of-lists (or a flat list) of claim dicts; return a flat
    # list; every claim MUST keep its `source`. Reject claims without a source.
    raise NotImplementedError("Implement merge_claims (see README.md).")


def annotate_conflict(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep BOTH values (with attribution + dates) when sources disagree (Task 5.6)."""
    # TODO: group by `metric`; for metrics with >1 distinct `value`, return an
    # annotation listing every observation (value, source, url, date, excerpt).
    raise NotImplementedError("Implement annotate_conflict (see README.md).")


def coverage_annotations(
    facets: list[str],
    claims: list[dict[str, Any]],
    errors: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Mark each facet 'supported' or a 'gap' (Task 5.3)."""
    # TODO: a facet with findings is supported; otherwise a gap (cite the matching
    # error's failure_type/attempted_query when one exists).
    raise NotImplementedError("Implement coverage_annotations (see README.md).")


def render_by_type(items: list[dict[str, Any]], content_type: str) -> str:
    """Render claims per content type: 'table' | 'prose' | 'list' (Task 5.6)."""
    # TODO: statistics -> markdown table; news -> prose; technical -> bulleted list.
    raise NotImplementedError("Implement render_by_type (see README.md).")


def classify_verification(claim: str) -> str:
    """Return 'simple' or 'complex' for a verification request (Sample Q9)."""
    # TODO: interpretive / causal / methodological / multi-source -> complex;
    # single lookups (date, name, statistic) -> simple.
    raise NotImplementedError("Implement classify_verification (see README.md).")


def verify(
    client: Any,
    claim: str,
    *,
    coordinator: Callable[[str], Any] | None = None,
    model: str = "claude-mock",
    max_tokens: int = 256,
) -> dict[str, Any]:
    """Verify a claim with the scoped-tool pattern (Sample Q9-A)."""
    # TODO: simple -> force the scoped verify_fact tool via one client call;
    # complex -> route back through the coordinator WITHOUT calling verify_fact.
    raise NotImplementedError("Implement verify (see README.md).")


def synthesize(
    topic: str,
    finding_lists: Any,
    *,
    facets: list[str],
    errors: list[dict[str, Any]] | None = None,
    content_type: str = "list",
) -> dict[str, Any]:
    """Merge findings into a cited report (provenance, conflicts, coverage)."""
    # TODO: merge_claims -> annotate_conflict -> coverage_annotations; separate
    # well-established from contested; build a claim->source provenance map and a
    # rendered report. Return a dict with those keys.
    raise NotImplementedError("Implement synthesize (see README.md).")
