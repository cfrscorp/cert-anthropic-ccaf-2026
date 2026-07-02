"""Deterministic tests for L20 — Error Propagation & Provenance in Synthesis.

These exercise Task Statements 5.3 (structured error context; access failure vs.
empty success; local recovery vs. propagation; coverage annotations) and 5.6
(claim→source preservation; conflict annotation; temporal dates; content-type
rendering). All offline and deterministic.

Run from labs/:  uv run pytest lab-20-error-propagation-provenance
Validate ref:     LAB_TARGET=solution uv run pytest lab-20-error-propagation-provenance
"""

from __future__ import annotations

import json

import pytest
from labkit import lab_module, lab_root

propagation = lab_module(__file__, "propagation")
provenance = lab_module(__file__, "provenance")


def _load_fixture() -> dict:
    with open(lab_root(__file__) / "findings.json", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Task 5.3 — error propagation
# --------------------------------------------------------------------------- #


def test_build_error_context_has_all_four_fields():
    """Structured error context must carry all four recovery-enabling fields."""
    ctx = propagation.build_error_context(
        failure_type="timeout",
        attempted="site:iea.org EV market share 2023",
        partial_results=[{"title": "IEA landing page"}],
        alternatives=["retry with a narrower query", "try BloombergNEF"],
    )
    for field in ("failure_type", "attempted", "partial_results", "alternatives"):
        assert field in ctx, f"missing structured field: {field}"
    assert ctx["failure_type"] == "timeout"
    assert ctx["attempted"] == "site:iea.org EV market share 2023"
    assert ctx["partial_results"] == [{"title": "IEA landing page"}]
    assert "retry with a narrower query" in ctx["alternatives"]


def test_build_error_context_defaults_empty_lists():
    """partial_results/alternatives default to [] (present, not missing)."""
    ctx = propagation.build_error_context("timeout", "some query")
    assert ctx["partial_results"] == []
    assert ctx["alternatives"] == []


def test_classify_result_timeout_is_access_failure():
    """A timeout is an access failure (retry-worthy), NOT an empty success."""
    assert (
        propagation.classify_result({"status": "error", "failure_type": "timeout"})
        == "access_failure"
    )
    assert propagation.classify_result({"timed_out": True}) == "access_failure"


def test_classify_result_empty_but_successful():
    """A completed query that found nothing is an empty success."""
    assert (
        propagation.classify_result({"status": "ok", "results": []})
        == "empty_success"
    )


def test_classify_result_with_data_is_success():
    """A completed query that returned data is a plain success."""
    assert (
        propagation.classify_result({"status": "ok", "results": [{"id": 1}]})
        == "success"
    )


def test_handle_subagent_failure_recovers_transient_locally():
    """A transient failure is resolved in place; the coordinator never sees it."""
    out = propagation.handle_subagent_failure(
        {
            "failure_type": "timeout",
            "attempted": "EV market share",
            "recovery_result": [{"title": "IEA EV Outlook"}],
        }
    )
    assert out["recovered_locally"] is True
    assert out["status"] == "recovered"
    assert out["result"] == [{"title": "IEA EV Outlook"}]


def test_handle_subagent_failure_propagates_hard_failure_with_partial_results():
    """A hard failure is propagated UP, carrying what was attempted + partials."""
    partial = [{"title": "cached snippet"}]
    out = propagation.handle_subagent_failure(
        {
            "failure_type": "permission_denied",
            "attempted": "internal doc lookup",
            "partial_results": partial,
            "alternatives": ["ask coordinator for credentials"],
        }
    )
    assert out["recovered_locally"] is False
    assert out["failure_type"] == "permission_denied"
    assert out["partial_results"] == partial
    assert out["attempted"] == "internal doc lookup"


def test_handle_subagent_failure_propagates_exhausted_transient():
    """A transient failure with no retries left is propagated, not swallowed."""
    out = propagation.handle_subagent_failure(
        {
            "failure_type": "timeout",
            "attempted": "q",
            "retries_exhausted": True,
            "partial_results": [{"x": 1}],
        }
    )
    assert out["recovered_locally"] is False
    assert out["partial_results"] == [{"x": 1}]


def test_coverage_annotations_marks_supported_and_gaps():
    """Well-supported topics and gap topics are annotated separately."""
    ann = propagation.coverage_annotations(
        [
            {"topic": "visual_arts", "sources": [{"url": "a"}]},
            {"topic": "music", "status": "gap", "reason": "search timed out"},
            {"topic": "film", "sources": []},
        ]
    )
    assert "visual_arts" in ann["well_supported"]
    gap_topics = {g["topic"] for g in ann["gaps"]}
    assert {"music", "film"} <= gap_topics


# --------------------------------------------------------------------------- #
# Task 5.6 — provenance & uncertainty
# --------------------------------------------------------------------------- #


def test_merge_claims_preserves_each_claims_source():
    """Every merged claim must still point at its source (from the fixture)."""
    fixture = _load_fixture()
    merged = provenance.merge_claims(fixture["findings"])
    assert len(merged) == 2
    for entry in merged:
        assert entry["source"] is not None
        # url or name must survive the merge
        assert entry["source"].get("url") or entry["source"].get("name")
    names = {m["source"]["name"] for m in merged}
    assert any("IEA" in n or "International Energy Agency" in n for n in names)
    assert any("BloombergNEF" in n for n in names)


def test_merge_claims_per_claim_source_overrides_default():
    """A claim carrying its own source beats the finding-level default source."""
    findings = [
        {
            "source": {"name": "Default Doc"},
            "claims": [
                "inherits default",
                {"claim": "has own source", "source": {"name": "Specific Doc"}},
            ],
        }
    ]
    merged = provenance.merge_claims(findings)
    by_text = {m["claim"]: m["source"]["name"] for m in merged}
    assert by_text["inherits default"] == "Default Doc"
    assert by_text["has own source"] == "Specific Doc"


def test_annotate_conflict_retains_both_values_and_attributions():
    """Conflicting stats are kept BOTH, attributed — never arbitrarily resolved."""
    fixture = _load_fixture()
    values = [
        {
            "value": f["claims"][0]["value"],
            "source": f["source"]["name"],
            "date": f["publication_date"],
        }
        for f in fixture["findings"]
    ]
    result = provenance.annotate_conflict(values)
    assert result["conflict"] is True
    assert result["resolved"] is False
    kept_values = {v["value"] for v in result["values"]}
    assert kept_values == {18, 14}  # both retained, neither dropped
    kept_sources = {v["source"] for v in result["values"]}
    assert len(kept_sources) == 2  # each value keeps its attribution


def test_annotate_conflict_no_conflict_when_values_agree():
    """Agreeing values are not flagged as a conflict."""
    result = provenance.annotate_conflict(
        [
            {"value": 20, "source": "A", "date": "2024-01-01"},
            {"value": 20, "source": "B", "date": "2024-02-01"},
        ]
    )
    assert result["conflict"] is False


def test_needs_temporal_flag():
    """A dated value is fine; an undated value must be flagged."""
    assert (
        provenance.needs_temporal_flag([{"value": 18, "date": "2024-04-23"}]) is False
    )
    assert provenance.needs_temporal_flag([{"value": 14}]) is True


def test_attach_dates_is_non_mutating():
    """attach_dates returns a dated copy without mutating the caller's claim."""
    claim = {"claim": "EVs reached 14%", "value": 14}
    dated = provenance.attach_dates(claim, "2023-06-06")
    assert dated["date"] == "2023-06-06"
    assert "date" not in claim  # original untouched


def test_render_by_type_financial_is_table():
    """Financial data renders as a markdown table (contains pipes + a rule)."""
    out = provenance.render_by_type(
        "financial", [{"metric": "EV share", "2022": "14%", "2023": "18%"}]
    )
    assert "|" in out
    assert "---" in out
    assert "EV share" in out


def test_render_by_type_news_is_prose():
    """News renders as prose — no table pipes, no bullet markers."""
    out = provenance.render_by_type(
        "news", ["EV adoption accelerated.", "Analysts cited falling battery costs."]
    )
    assert "|" not in out
    assert not out.lstrip().startswith("- ")
    assert "EV adoption accelerated." in out


def test_render_by_type_technical_is_list():
    """Technical findings render as a bulleted list."""
    out = provenance.render_by_type(
        "technical", ["Uses LFP chemistry", "Supports 800V charging"]
    )
    lines = out.splitlines()
    assert all(line.startswith("- ") for line in lines)
    assert len(lines) == 2


def test_render_by_type_unknown_raises():
    """An unknown content type is a programming error, not a silent default."""
    with pytest.raises(ValueError):
        provenance.render_by_type("spreadsheet", [{"a": 1}])
