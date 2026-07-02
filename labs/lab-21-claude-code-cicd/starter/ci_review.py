#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""CI/CD glue for Claude Code code review (Task Statement 3.6) — STARTER.

Implement the four functions below so the offline half of a CI review pipeline
works: parse Claude's schema-enforced JSON, format PR comments, dedupe against a
prior run, and assert the workflow runs Claude non-interactively.

Context: in CI you invoke Claude Code like this (see .github/workflows/claude-review.yml)::

    claude -p "<review prompt>" --output-format json --json-schema review-schema.json

- ``-p`` / ``--print`` makes the run non-interactive (Sample Q10 — NOT a
  ``CLAUDE_HEADLESS`` env var, ``--batch``, or ``< /dev/null``).
- ``--output-format json`` + ``--json-schema`` force machine-parseable findings.

Public API (must match solution/):

    parse_findings(json_text, schema)          -> list[dict]
    to_pr_comments(findings)                    -> list[dict]
    dedupe_against_prior(new_findings, prior)   -> list[dict]
    workflow_uses_print_flag(workflow_yaml)     -> bool

Keep everything pure — no Claude calls. Tests inject the JSON/schema/workflow.

A runnable CLI is provided at the bottom (already wired). Once the functions are
implemented it works via ``uv run ci_review.py --help``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import yaml  # noqa: F401  (you'll want this for workflow_uses_print_flag)

__all__ = [
    "parse_findings",
    "to_pr_comments",
    "dedupe_against_prior",
    "workflow_uses_print_flag",
]

__version__ = "0.1.0"


def parse_findings(json_text: str, schema: dict) -> list[dict]:
    """Parse Claude's JSON review output and validate it against ``schema``.

    ``json_text`` is the stdout of ``claude -p ... --output-format json
    --json-schema review-schema.json`` — an object ``{"findings": [ ... ]}``.

    Steps:
      1. json.loads the text; raise ValueError on invalid JSON.
      2. Validate the parsed object against ``schema`` (at minimum: required
         keys, types, and the severity enum). Raise ValueError if it does not
         conform — CI must fail loudly, not post malformed comments.
      3. Return the ``findings`` list.

    Note: ``jsonschema`` is NOT a dependency; write a small validator, or lean on
    the fields you know the schema requires.
    """
    # TODO: parse, validate against schema, return data["findings"].
    raise NotImplementedError("parse_findings: json.loads + schema validation")


def to_pr_comments(findings: list[dict]) -> list[dict]:
    """Map validated findings to GitHub inline review comments.

    Return a list of ``{"path": str, "line": int, "body": str}`` dicts (the
    shape GitHub's "create review comment" API expects). Pull ``path`` and
    ``line`` from each finding's ``location``; build ``body`` from severity,
    issue, suggested_fix, and detected_pattern so the comment is actionable.
    """
    # TODO: build one comment dict per finding.
    raise NotImplementedError("to_pr_comments: format path/line/body")


def dedupe_against_prior(new_findings: list[dict], prior_findings: list[dict]) -> list[dict]:
    """Return only findings not already present in ``prior_findings``.

    On a re-run after new commits, prior findings are fed back in so only NEW or
    still-unaddressed issues are reported (no duplicate comments each push).
    Choose a stable identity key for a finding (e.g. path + line +
    detected_pattern + issue) and drop any new finding whose key appears in the
    prior set. Preserve the order of ``new_findings``.
    """
    # TODO: filter new_findings by a stable identity key.
    raise NotImplementedError("dedupe_against_prior: drop already-reported findings")


def workflow_uses_print_flag(workflow_yaml: str) -> bool:
    """True if the workflow invokes ``claude`` with ``-p`` or ``--print``.

    Guards the Sample Q10 fix: bare ``claude "..."`` hangs in CI waiting for
    input. Only ``-p`` / ``--print`` counts — an env var, ``--batch``, or a
    ``< /dev/null`` redirect must return False.

    Parse the YAML, walk jobs -> steps -> ``run`` scripts, and check whether any
    ``claude`` command carries the flag as a distinct token.
    """
    # TODO: inspect the workflow's run steps for `claude ... -p/--print`.
    raise NotImplementedError("workflow_uses_print_flag: scan run steps for -p/--print")


# --------------------------------------------------------------------------- #
# CLI (already wired — works once the functions above are implemented)
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ci_review.py",
        description=(
            "Parse Claude Code's JSON review output, dedupe against prior "
            "findings, and emit GitHub inline PR comments — the offline half of "
            "a `claude -p ... --output-format json --json-schema` CI pipeline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Validate a workflow really runs Claude non-interactively (-p/--print)\n"
            "  uv run ci_review.py --check-workflow .github/workflows/claude-review.yml\n\n"
            "  # Parse Claude's output and print PR comments as JSON\n"
            "  uv run ci_review.py --findings review.json --schema review-schema.json\n\n"
            "  # Same, but drop issues already reported on a prior run\n"
            "  uv run ci_review.py --findings review.json --schema review-schema.json \\\n"
            "      --prior prior_findings.json --post\n\n"
            "  # Print the version\n"
            "  uv run ci_review.py --version\n"
        ),
    )
    parser.add_argument("--findings", help="path to Claude's JSON output ({\"findings\": [...]})")
    parser.add_argument("--schema", help="path to review-schema.json used to validate findings")
    parser.add_argument("--prior", help="path to prior_findings.json to dedupe against")
    parser.add_argument(
        "--check-workflow",
        metavar="FILE",
        help="validate a workflow YAML invokes `claude` with -p/--print, then exit",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="emit PR comments (default action when --findings is given)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.check_workflow:
        text = open(args.check_workflow, encoding="utf-8").read()
        ok = workflow_uses_print_flag(text)
        print("OK: workflow runs claude with -p/--print" if ok
              else "ERROR: no `claude -p/--print` command found (CI would hang)")
        return 0 if ok else 1

    if not args.findings or not args.schema:
        print("Nothing to do. Provide --findings + --schema, or --check-workflow. "
              "See --help.", file=sys.stderr)
        return 2

    schema: Any = json.loads(open(args.schema, encoding="utf-8").read())
    findings = parse_findings(open(args.findings, encoding="utf-8").read(), schema)

    if args.prior:
        prior_doc = json.loads(open(args.prior, encoding="utf-8").read())
        prior = prior_doc["findings"] if isinstance(prior_doc, dict) else prior_doc
        findings = dedupe_against_prior(findings, prior)

    print(json.dumps(to_pr_comments(findings), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
