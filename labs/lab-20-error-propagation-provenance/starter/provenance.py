"""Starter scaffold — provenance & uncertainty in multi-source synthesis (5.6).

Implement the functions below so synthesis preserves attribution, keeps
conflicting values instead of picking one, flags undated statistics, and renders
each content type in its natural form. See README.md for the full brief.

The public API here MUST match ``solution/provenance.py`` so the same tests run
against both. Replace every ``raise NotImplementedError`` with real logic.

Key semantics to get right:

* ``merge_claims`` keeps every claim's source (url/doc name/excerpt) through the
  flatten/merge.
* ``annotate_conflict`` retains BOTH conflicting values with attribution; it does
  not resolve them.
* ``needs_temporal_flag`` / ``attach_dates`` handle publication/collection dates.
* ``render_by_type`` renders financial → table, news → prose, technical → list.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-20-error-propagation-provenance
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "merge_claims",
    "annotate_conflict",
    "needs_temporal_flag",
    "attach_dates",
    "render_by_type",
]


def merge_claims(findings: list[dict]) -> list[dict]:
    """Flatten findings into claims that each keep their source.

    Each finding has a ``claims`` list and (optionally) a top-level ``source``.
    Return a flat list of {"claim": <text>, "source": {...}} where every claim
    still points at where it came from. A claim dict's own ``source`` wins over
    the finding's default source.
    """
    # TODO: iterate findings and their claims, preserving each claim's source.
    raise NotImplementedError


def annotate_conflict(values: list[dict]) -> dict:
    """Retain conflicting values with attribution instead of picking one.

    ``values`` is a list of {"value", "source", "date"}. Return a dict that keeps
    every value with its source, marks whether there is a conflict, and leaves it
    unresolved (do NOT choose a winner).
    """
    # TODO: keep all values with attribution; set conflict=True when they differ.
    raise NotImplementedError


def needs_temporal_flag(claims: list[dict]) -> bool:
    """Return True if any quantitative/temporal claim is missing a date."""
    # TODO: flag a claim that carries a value (or temporal marker) but no date.
    raise NotImplementedError


def attach_dates(claim: dict, date: str) -> dict:
    """Return a copy of ``claim`` with ``date`` attached (do not mutate input)."""
    # TODO: return a new dict with the date attached.
    raise NotImplementedError


def render_by_type(content_type: str, data: Any) -> str:
    """Render financial → table, news → prose, technical → list.

    Raise ValueError for an unknown content_type.
    """
    # TODO: dispatch on content_type to the right renderer.
    raise NotImplementedError
