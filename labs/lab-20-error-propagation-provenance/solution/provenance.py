"""Reference solution — provenance & uncertainty in multi-source synthesis (5.6).

Synthesis is where attribution goes to die. When findings from several subagents
are compressed into one report, the naive summarizer keeps the *sentences* and
drops the *sources*, silently picks one number when two credible sources
disagree, and flattens everything into uniform prose. Task Statement 5.6 says do
the opposite:

* Preserve **claim → source** mappings (url / document name / excerpt) all the
  way through synthesis, merging rather than discarding them.
* When credible sources conflict, **annotate both values with attribution** —
  never arbitrarily pick one.
* Require **publication / collection dates** so a value measured later is not
  misread as contradicting an earlier one (a temporal difference, not a conflict).
* Render each content type in its natural form — **financial as tables, news as
  prose, technical findings as lists** — instead of one uniform format.

Imported by the test suite; not a shell script, so the PEP 723 / argparse
conventions do not apply (docstrings instead).
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
    """Flatten per-subagent findings into claims that keep their source.

    Each ``finding`` is a dict with a ``claims`` list and (optionally) a
    top-level ``source`` describing where those claims came from. A claim may be
    a bare string (inherits the finding's source) or a dict carrying its own
    ``source`` (which wins). The result is a flat list of::

        {"claim": <text>, "source": {"name"/"url"/"excerpt": ...}}

    The load-bearing property: **every** merged claim still points at its source.
    That mapping is what lets the final report cite where each statement came from
    instead of asserting facts anonymously.
    """
    merged: list[dict] = []
    for finding in findings:
        default_source = finding.get("source")
        for claim in finding.get("claims", []):
            if isinstance(claim, dict):
                source = claim.get("source", default_source)
                text = claim.get("claim", claim.get("text"))
                entry = {"claim": text, "source": source}
                # Preserve a per-claim date if the subagent recorded one.
                if "date" in claim:
                    entry["date"] = claim["date"]
            else:
                entry = {"claim": claim, "source": default_source}
            merged.append(entry)
    return merged


def annotate_conflict(values: list[dict]) -> dict:
    """Retain conflicting values from credible sources, each with attribution.

    ``values`` is a list of ``{"value": ..., "source": ..., "date": ...}``. When
    credible sources disagree, the synthesis agent must NOT silently choose one
    (Task 5.6). It records *both*, attributed, and marks the conflict unresolved
    so the coordinator (or a human) can reconcile with full information.

    Returns::

        {"conflict": bool,
         "resolved": False,
         "values": [{"value", "source", "date"}, ...],
         "note": "..."}
    """
    retained = [
        {
            "value": v.get("value"),
            "source": v.get("source"),
            "date": v.get("date"),
        }
        for v in values
    ]
    # Distinct values (order-preserving, no hashing assumption) => a real conflict.
    distinct: list = []
    for entry in retained:
        if entry["value"] not in distinct:
            distinct.append(entry["value"])

    return {
        "conflict": len(distinct) > 1,
        "resolved": False,
        "values": retained,
        "note": (
            "Conflicting values from credible sources retained with attribution; "
            "not arbitrarily resolved. Coordinator/human to reconcile "
            "(check publication dates before treating as a contradiction)."
        ),
    }


def needs_temporal_flag(claims: list[dict]) -> bool:
    """Return True if any quantitative claim lacks a date.

    A statistic without a date is dangerous in synthesis: a value collected in
    2023 and another collected in 2024 look like a contradiction when really the
    world changed between measurements. If a claim carries a value (or is marked
    temporal) but has no date, it must be flagged so a date can be attached before
    synthesis compares it with anything else.
    """
    for claim in claims:
        has_value = "value" in claim or bool(claim.get("temporal"))
        has_date = bool(claim.get("date"))
        if has_value and not has_date:
            return True
    return False


def attach_dates(claim: dict, date: str) -> dict:
    """Return a copy of ``claim`` with a publication/collection ``date`` attached.

    Non-mutating: the caller's claim is left untouched. Attaching dates is the fix
    ``needs_temporal_flag`` points to — once every value carries its date, a later
    measurement is read as *newer*, not *contradictory*.
    """
    updated = dict(claim)
    updated["date"] = date
    return updated


def render_by_type(content_type: str, data: Any) -> str:
    """Render content in its natural form instead of one uniform format (5.6).

    * ``"financial"`` → a markdown **table** (rows of dicts, or a single dict).
    * ``"news"``      → **prose** (a string, or sentences joined into a paragraph).
    * ``"technical"`` → a bulleted **list** (one ``- item`` per line).
    """
    if content_type == "financial":
        return _render_table(data)
    if content_type == "news":
        return _render_prose(data)
    if content_type == "technical":
        return _render_list(data)
    raise ValueError(
        f"Unknown content_type {content_type!r}; "
        "expected 'financial', 'news', or 'technical'."
    )


def _render_table(rows: Any) -> str:
    """Financial data as a markdown table."""
    if isinstance(rows, dict):
        rows = [rows]
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def _render_prose(data: Any) -> str:
    """News as a single prose paragraph."""
    if isinstance(data, str):
        return data
    return " ".join(str(item) for item in data)


def _render_list(data: Any) -> str:
    """Technical findings as a bulleted list."""
    if isinstance(data, str):
        data = [data]
    return "\n".join(f"- {item}" for item in data)
