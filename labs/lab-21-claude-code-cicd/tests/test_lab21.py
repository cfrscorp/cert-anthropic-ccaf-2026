"""Deterministic tests for Lab 21 — Claude Code in CI/CD (Task Statement 3.6).

These pass against solution/ (LAB_TARGET=solution) and fail against an
unfinished starter/ (whose ci_review.py functions raise NotImplementedError).

They exercise the offline half of a CI review pipeline:

- parse_findings validates the sample Claude output against review-schema.json,
  and rejects a malformed output.
- to_pr_comments maps location/issue/severity/fix into GitHub inline comments.
- dedupe_against_prior drops already-reported findings and keeps new ones.
- workflow_uses_print_flag is True for a workflow that runs `claude -p ...`
  (the Sample Q10 fix) and False for one that omits it.

Config artifacts (schema, sample output, prior findings, workflow) are read from
the ACTIVE target dir (starter/ or solution/) via labkit.target_dir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labkit import lab_module, target_dir

ci = lab_module(__file__, "ci_review")
TARGET = target_dir(__file__)


def _read(name: str) -> str:
    return (TARGET / name).read_text(encoding="utf-8")


def _schema() -> dict:
    return json.loads(_read("review-schema.json"))


def _sample_findings_json() -> str:
    return _read("sample_claude_output.json")


def _prior_findings() -> list[dict]:
    return json.loads(_read("prior_findings.json"))["findings"]


# --------------------------------------------------------------------------- #
# parse_findings
# --------------------------------------------------------------------------- #

def test_parse_findings_validates_sample_output():
    findings = ci.parse_findings(_sample_findings_json(), _schema())
    assert isinstance(findings, list)
    assert len(findings) == 3
    # Fields the schema requires are present on every finding.
    for f in findings:
        assert set(f) >= {"location", "issue", "severity", "suggested_fix", "detected_pattern"}
        assert set(f["location"]) >= {"path", "line"}
    severities = {f["severity"] for f in findings}
    assert severities <= {"critical", "high", "medium", "low", "info"}


def test_parse_findings_rejects_invalid_json():
    with pytest.raises(ValueError):
        ci.parse_findings("{not valid json", _schema())


def test_parse_findings_rejects_malformed_output():
    # Missing required 'severity' and a bad line type -> must fail schema validation.
    malformed = json.dumps(
        {
            "findings": [
                {
                    "location": {"path": "a.py", "line": "oops"},
                    "issue": "something",
                    "suggested_fix": "fix it",
                    "detected_pattern": "x",
                }
            ]
        }
    )
    with pytest.raises(ValueError):
        ci.parse_findings(malformed, _schema())


def test_parse_findings_rejects_bad_severity_enum():
    bad = json.dumps(
        {
            "findings": [
                {
                    "location": {"path": "a.py", "line": 3},
                    "issue": "x",
                    "severity": "catastrophic",
                    "suggested_fix": "y",
                    "detected_pattern": "z",
                }
            ]
        }
    )
    with pytest.raises(ValueError):
        ci.parse_findings(bad, _schema())


# --------------------------------------------------------------------------- #
# to_pr_comments
# --------------------------------------------------------------------------- #

def test_to_pr_comments_maps_fields():
    findings = ci.parse_findings(_sample_findings_json(), _schema())
    comments = ci.to_pr_comments(findings)
    assert len(comments) == len(findings)
    for comment, finding in zip(comments, findings):
        assert set(comment) >= {"path", "line", "body"}
        assert comment["path"] == finding["location"]["path"]
        assert comment["line"] == finding["location"]["line"]
        assert isinstance(comment["body"], str) and comment["body"].strip()
        # Body carries the actionable context.
        assert finding["issue"] in comment["body"]
        assert finding["suggested_fix"] in comment["body"]
        assert finding["detected_pattern"] in comment["body"]


# --------------------------------------------------------------------------- #
# dedupe_against_prior
# --------------------------------------------------------------------------- #

def test_dedupe_drops_already_reported_and_keeps_new():
    new = ci.parse_findings(_sample_findings_json(), _schema())
    prior = _prior_findings()
    result = ci.dedupe_against_prior(new, prior)
    # The SQL-injection finding was reported before -> dropped; the other 2 remain.
    assert len(result) == 2
    patterns = {f["detected_pattern"] for f in result}
    assert "f-string-in-sql-execute" not in patterns
    assert patterns == {"bare-except-swallow", "missing-branch-test"}


def test_dedupe_with_empty_prior_returns_all():
    new = ci.parse_findings(_sample_findings_json(), _schema())
    assert ci.dedupe_against_prior(new, []) == new


def test_dedupe_preserves_order():
    new = ci.parse_findings(_sample_findings_json(), _schema())
    result = ci.dedupe_against_prior(new, [])
    assert [f["location"]["line"] for f in result] == [42, 118, 205]


# --------------------------------------------------------------------------- #
# workflow_uses_print_flag  (Sample Question 10)
# --------------------------------------------------------------------------- #

def test_workflow_uses_print_flag_true_for_target_workflow():
    workflow = _read(".github/workflows/claude-review.yml")
    assert ci.workflow_uses_print_flag(workflow) is True


def test_workflow_uses_print_flag_false_when_missing():
    # Bare `claude "..."` — the Sample Q10 hang. No -p / --print anywhere.
    bad = """
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - run: |
          claude "Analyze this pull request for security issues" > review.json
"""
    assert ci.workflow_uses_print_flag(bad) is False


def test_workflow_distractors_do_not_count_as_print_flag():
    # CLAUDE_HEADLESS env var, --batch flag, and stdin redirect are all WRONG
    # (Sample Q10 distractors) and must not be accepted as non-interactive.
    distractors = """
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - env:
          CLAUDE_HEADLESS: "true"
        run: |
          claude --batch "Analyze this PR" < /dev/null > review.json
"""
    assert ci.workflow_uses_print_flag(distractors) is False


def test_workflow_accepts_long_print_flag():
    good = """
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - run: claude --print "Review this diff" --output-format json > review.json
"""
    assert ci.workflow_uses_print_flag(good) is True
