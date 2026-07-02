"""Reference solution — synthesis with provenance, conflict handling, verify_fact.

Task Statement 5.6 ("Preserve information provenance and handle uncertainty in
multi-source synthesis"), 2.3 (scoped tools), and Sample Question 9.

What synthesis must get right:

- **Provenance survives the merge.** :func:`merge_claims` never drops a claim's
  ``source`` — attribution is not lost during aggregation (Task 5.6).
- **Conflicts are annotated, not resolved by fiat.** :func:`annotate_conflict`
  keeps BOTH values with source attribution and publication dates rather than
  picking one; differing dates may mean change-over-time, not contradiction
  (Task 5.6).
- **Coverage gaps are explicit.** :func:`coverage_annotations` marks which facets
  are well-supported vs. which are gaps because a source was unavailable (Task 5.3).
- **Typed rendering.** :func:`render_by_type` renders statistics as a table, news
  as prose, technical findings as a list — not everything as one uniform blob.
- **Scoped verification.** :func:`verify` sends the 85% simple lookups to the
  scoped ``verify_fact`` tool and routes the 15% complex cases back through the
  coordinator (Sample Q9-A / Task 2.3).

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

from typing import Any, Callable

from agents import verify_fact_schema

__all__ = [
    "merge_claims",
    "annotate_conflict",
    "coverage_annotations",
    "render_by_type",
    "classify_verification",
    "verify",
    "synthesize",
]

# Markers that make a verification "complex" — needing real investigation rather
# than a single lookup. Everything else is treated as a simple fact-check.
_COMPLEX_MARKERS = (
    "whether", "why", "how does", "methodology", "causal", "cause", "interpret",
    "assess", "evaluate", "implication", "bias", "trade-off", "tradeoff",
    "compare across", "reconcile", "root cause", "significance",
)


def _as_claim_lists(finding_lists: Any) -> list[list[dict[str, Any]]]:
    """Normalize the input to a list-of-lists of claim dicts.

    Accepts either ``[[claim, ...], [claim, ...]]`` (per-subagent) or a single
    flat ``[claim, ...]`` list, so callers can pass whichever they have.
    """
    if not finding_lists:
        return []
    first = finding_lists[0]
    if isinstance(first, dict):
        return [list(finding_lists)]  # a single flat list of claims
    return [list(lst) for lst in finding_lists]


def merge_claims(finding_lists: Any) -> list[dict[str, Any]]:
    """Flatten per-subagent findings into one list, preserving each claim's source.

    Provenance is the whole point: the returned claims retain their ``source``
    (name, url, date). A claim missing a source is a bug upstream — we raise so it
    surfaces rather than silently shipping an unattributed claim (Task 5.6).
    """
    merged: list[dict[str, Any]] = []
    for lst in _as_claim_lists(finding_lists):
        for claim in lst:
            if "source" not in claim:
                raise ValueError(
                    f"claim without provenance cannot be merged: {claim!r}"
                )
            merged.append(dict(claim))  # copy keeps the source mapping intact
    return merged


def annotate_conflict(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find claims that report the same metric with different values.

    Returns one annotation per conflicting metric, KEEPING every observation with
    its source name, url, and date. Nothing is discarded and no value is chosen —
    the report presents both (Task 5.6). Differing dates are called out so a
    temporal change is not mistaken for a contradiction.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        metric = c.get("metric")
        if metric:
            groups.setdefault(metric, []).append(c)

    conflicts: list[dict[str, Any]] = []
    for metric, group in groups.items():
        distinct_values = {c.get("value") for c in group}
        if len(distinct_values) <= 1:
            continue  # agreement (or a single observation) is not a conflict
        observations = [
            {
                "value": c.get("value"),
                "source": c["source"].get("name"),
                "url": c["source"].get("url"),
                "date": c["source"].get("date"),
                "excerpt": c.get("excerpt"),
            }
            for c in group
        ]
        dates = sorted(o["date"] for o in observations if o.get("date"))
        conflicts.append(
            {
                "metric": metric,
                "conflict": True,
                "observations": observations,
                "note": (
                    "Sources report differing values; both are retained with "
                    "attribution and dates rather than selecting one. Publication "
                    f"dates span {dates[0]}..{dates[-1]}; the difference may reflect "
                    "change over time rather than contradiction."
                    if len(dates) >= 2
                    else "Sources report differing values; both are retained with "
                    "attribution rather than selecting one."
                ),
            }
        )
    return conflicts


def coverage_annotations(
    facets: list[str],
    claims: list[dict[str, Any]],
    errors: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Mark each facet well-supported vs. a coverage gap (Task 5.3).

    A facet with sourced findings is ``"supported"``. A facet with none is a
    ``"gap"``; if a structured error explains why (e.g. a timeout), the reason
    cites the failure type and attempted query so the gap is traceable.
    """
    errors = errors or []
    err_by_facet = {e.get("facet"): e for e in errors if e.get("facet")}
    supported = {c.get("facet") for c in claims}

    out: list[dict[str, Any]] = []
    for facet in facets:
        if facet in supported:
            out.append(
                {
                    "facet": facet,
                    "status": "supported",
                    "reason": "one or more sourced findings",
                }
            )
        else:
            err = err_by_facet.get(facet)
            if err:
                reason = (
                    f"no findings: {err.get('failure_type')} while attempting "
                    f"{err.get('attempted_query')!r}"
                )
            else:
                reason = "no sources available for this facet"
            out.append({"facet": facet, "status": "gap", "reason": reason})
    return out


def render_by_type(items: list[dict[str, Any]], content_type: str) -> str:
    """Render claims according to their content type (Task 5.6).

    - ``"table"``  → a Markdown table (best for statistics / financial data).
    - ``"prose"``  → attributed sentences (best for news).
    - ``"list"``   → a bulleted list (best for technical findings).

    Rendering everything as one uniform format is the anti-pattern this avoids.
    """
    if not items:
        return "_No findings._"

    if content_type == "table":
        rows = ["| Claim | Value | Source | Date |", "|---|---|---|---|"]
        for c in items:
            src = c.get("source", {})
            rows.append(
                f"| {c.get('claim', '')} | {c.get('value', '') or ''} | "
                f"{src.get('name', '')} | {src.get('date', '')} |"
            )
        return "\n".join(rows)

    if content_type == "prose":
        sentences = []
        for c in items:
            src = c.get("source", {})
            sentences.append(
                f"{c.get('claim', '').rstrip('.')} "
                f"({src.get('name', '')}, {src.get('date', '')})."
            )
        return " ".join(sentences)

    # default: bulleted list
    lines = []
    for c in items:
        src = c.get("source", {})
        lines.append(
            f"- {c.get('claim', '')} "
            f"[{src.get('name', '')}, {src.get('date', '')}]"
        )
    return "\n".join(lines)


def classify_verification(claim: str) -> str:
    """Classify a verification as ``"simple"`` or ``"complex"`` (Sample Q9).

    Simple = a single lookup (a date, a name, one statistic) — ~85% of cases.
    Complex = interpretive / causal / multi-source — must go back through the
    coordinator to the web_search subagent.
    """
    text = str(claim).lower()
    if any(marker in text for marker in _COMPLEX_MARKERS):
        return "complex"
    return "simple"


def verify(
    client: Any,
    claim: str,
    *,
    coordinator: Callable[[str], Any] | None = None,
    model: str = "claude-mock",
    max_tokens: int = 256,
) -> dict[str, Any]:
    """Verify a claim, applying the scoped-tool pattern from Sample Q9-A.

    Simple lookups use the synthesis agent's own scoped ``verify_fact`` tool (one
    call, no coordinator round-trip). Complex verifications are routed back
    through the coordinator — the synthesis agent is NOT given the full search
    toolset (least privilege, Task 2.3).

    Returns a dict describing how verification was handled and its result.
    """
    kind = classify_verification(claim)

    if kind == "complex":
        # Do NOT call verify_fact. Hand back to the coordinator.
        if coordinator is not None:
            routed = coordinator(claim)
            return {
                "kind": "complex",
                "verified_via": "coordinator",
                "route": "coordinator",
                "claim": claim,
                "result": routed,
            }
        return {
            "kind": "complex",
            "verified_via": "coordinator",
            "route": "coordinator",
            "claim": claim,
            "result": None,
        }

    # Simple lookup: force the scoped verify_fact tool.
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": f"Verify this simple fact: {claim}"}],
        tools=[verify_fact_schema()],
        tool_choice={"type": "tool", "name": "verify_fact"},
    )
    blocks = [b for b in resp.tool_use_blocks() if b.name == "verify_fact"]
    return {
        "kind": "simple",
        "verified_via": "verify_fact",
        "route": "synthesis",
        "claim": claim,
        "result": blocks[0].input if blocks else None,
    }


def render_report(
    topic: str,
    well_established: list[dict[str, Any]],
    contested: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    content_type: str,
) -> str:
    """Assemble the final Markdown report with explicit sections (Task 5.6)."""
    parts = [f"# Research report: {topic}", "", "## Well-established findings", ""]
    parts.append(render_by_type(well_established, content_type))
    parts.append("")
    parts.append("## Contested findings")
    parts.append("")
    if contested:
        for c in contested:
            parts.append(f"### {c['metric']} (conflicting sources)")
            for o in c["observations"]:
                parts.append(
                    f"- **{o['value']}** — {o['source']} ({o['date']})"
                    + (f": {o['excerpt']}" if o.get("excerpt") else "")
                )
            parts.append(f"> {c['note']}")
            parts.append("")
    else:
        parts.append("_No conflicts detected._")
        parts.append("")
    parts.append("## Coverage")
    parts.append("")
    for cov in coverage:
        marker = "OK" if cov["status"] == "supported" else "GAP"
        parts.append(f"- [{marker}] {cov['facet']}: {cov['reason']}")
    return "\n".join(parts)


def synthesize(
    topic: str,
    finding_lists: Any,
    *,
    facets: list[str],
    errors: list[dict[str, Any]] | None = None,
    content_type: str = "list",
) -> dict[str, Any]:
    """Merge findings into a cited report preserving provenance and conflicts.

    Returns a dict with the merged claims, well-established vs. contested
    findings, coverage annotations, an explicit claim->source provenance map, and
    the rendered Markdown report.
    """
    merged = merge_claims(finding_lists)
    conflicts = annotate_conflict(merged)
    coverage = coverage_annotations(facets, merged, errors=errors)

    conflict_metrics = {c["metric"] for c in conflicts}
    well_established = [c for c in merged if c.get("metric") not in conflict_metrics]

    provenance = [{"claim": c["claim"], "source": c["source"]} for c in merged]
    report_markdown = render_report(
        topic, well_established, conflicts, coverage, content_type
    )

    return {
        "topic": topic,
        "claims": merged,
        "well_established": well_established,
        "contested": conflicts,
        "coverage": coverage,
        "provenance": provenance,
        "report_markdown": report_markdown,
    }
