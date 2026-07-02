#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""CI/CD glue for Claude Code code review (Task Statement 3.6) — REFERENCE SOLUTION.

Claude Code is invoked non-interactively in CI with::

    claude -p "<review prompt>" --output-format json --json-schema review-schema.json

The ``-p`` / ``--print`` flag is what makes the run non-interactive: Claude reads
the prompt, writes the result to stdout, and exits instead of waiting for
interactive input (the fix in Sample Question 10 — *not* a ``CLAUDE_HEADLESS``
env var, a ``--batch`` flag, or a ``< /dev/null`` redirect). ``--output-format
json`` + ``--json-schema`` force machine-parseable, schema-compliant findings so
the pipeline can post them as inline PR comments.

This module is the deterministic, offline half of that pipeline: it parses and
validates Claude's JSON output, turns findings into PR comments, drops findings
already reported on a prior run, and asserts a workflow actually passes ``-p``.

Public API (must match starter/):

    parse_findings(json_text, schema)          -> list[dict]
    to_pr_comments(findings)                    -> list[dict]
    dedupe_against_prior(new_findings, prior)   -> list[dict]
    workflow_uses_print_flag(workflow_yaml)     -> bool

No Claude calls here: the schema-enforced JSON *is* Claude's contribution; this
code consumes it. Everything is pure so tests run deterministically.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from typing import Any

import yaml

__all__ = [
    "parse_findings",
    "to_pr_comments",
    "dedupe_against_prior",
    "workflow_uses_print_flag",
]

__version__ = "1.0.0"


# --------------------------------------------------------------------------- #
# Minimal JSON-Schema validator (draft-07 subset — no extra deps)
# --------------------------------------------------------------------------- #

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def _type_ok(value: Any, json_type: str) -> bool:
    """True if ``value`` matches the JSON Schema ``type`` (bools are not ints)."""
    expected = _TYPE_MAP[json_type]
    if json_type in ("integer", "number") and isinstance(value, bool):
        return False  # JSON bools must not satisfy numeric types
    return isinstance(value, expected)


def _validate(instance: Any, schema: dict, path: str = "$") -> list[str]:
    """Return a list of validation error strings (empty == valid).

    Supports the keyword subset used by ``review-schema.json``: ``type``,
    ``enum``, ``required``, ``properties``, ``additionalProperties`` (bool),
    ``items``, ``minimum``, ``minLength``, ``minItems``.
    """
    errors: list[str] = []

    json_type = schema.get("type")
    if json_type is not None and not _type_ok(instance, json_type):
        errors.append(f"{path}: expected type {json_type!r}, got {type(instance).__name__}")
        return errors  # further checks assume the type held

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']!r}")

    if isinstance(instance, str) and "minLength" in schema:
        if len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                errors.extend(_validate(item, item_schema, f"{path}[{i}]"))

    if isinstance(instance, dict):
        props: dict = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required property {req!r}")
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}: additional property {key!r} not allowed")
        for key, subschema in props.items():
            if key in instance and isinstance(subschema, dict):
                errors.extend(_validate(instance[key], subschema, f"{path}.{key}"))

    return errors


# --------------------------------------------------------------------------- #
# 1) Parse + validate Claude's structured output
# --------------------------------------------------------------------------- #

def parse_findings(json_text: str, schema: dict) -> list[dict]:
    """Parse Claude's JSON review output and validate it against ``schema``.

    ``json_text`` is the stdout of ``claude -p ... --output-format json
    --json-schema review-schema.json`` — an object of the form
    ``{"findings": [ ... ]}``. Returns the ``findings`` list.

    Raises ``ValueError`` if the text is not valid JSON or if it does not
    satisfy the schema (``--json-schema`` makes this rare in production, but CI
    must fail loudly rather than post malformed comments).
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude output is not valid JSON: {exc}") from exc

    errors = _validate(data, schema)
    if errors:
        raise ValueError("Claude output failed schema validation: " + "; ".join(errors))

    return list(data["findings"])


# --------------------------------------------------------------------------- #
# 2) Format findings as inline PR comments
# --------------------------------------------------------------------------- #

def to_pr_comments(findings: list[dict]) -> list[dict]:
    """Map validated findings to GitHub inline review comments.

    Each comment is ``{"path": str, "line": int, "body": str}`` — the shape the
    GitHub "create review comment" API expects. The body surfaces severity, the
    issue, the suggested fix, and the detected pattern so the developer sees
    actionable context directly in the diff.
    """
    comments: list[dict] = []
    for f in findings:
        loc = f["location"]
        body = (
            f"**[{f['severity'].upper()}] Claude Code review**\n\n"
            f"{f['issue']}\n\n"
            f"**Suggested fix:** {f['suggested_fix']}\n\n"
            f"_Detected pattern: `{f['detected_pattern']}`_"
        )
        comments.append({"path": loc["path"], "line": loc["line"], "body": body})
    return comments


# --------------------------------------------------------------------------- #
# 3) Dedupe against previously reported findings
# --------------------------------------------------------------------------- #

def _finding_key(finding: dict) -> tuple:
    """Stable identity for a finding: where it is, what it is, and why it fired.

    Keying on (path, line, detected_pattern, issue) means a re-run reports a
    finding again only if it is genuinely new or still unaddressed — the same
    issue at the same place is treated as already-reported and suppressed.
    """
    loc = finding.get("location", {})
    return (
        loc.get("path"),
        loc.get("line"),
        finding.get("detected_pattern"),
        finding.get("issue"),
    )


def dedupe_against_prior(new_findings: list[dict], prior_findings: list[dict]) -> list[dict]:
    """Return only findings not already present in ``prior_findings``.

    When a review re-runs after new commits, prior findings are fed back in so
    Claude (and this filter) report only NEW or still-unaddressed issues,
    avoiding duplicate PR comments on every push. Order of ``new_findings`` is
    preserved.
    """
    already_seen = {_finding_key(f) for f in prior_findings}
    return [f for f in new_findings if _finding_key(f) not in already_seen]


# --------------------------------------------------------------------------- #
# 4) Assert the workflow runs Claude non-interactively (Sample Q10)
# --------------------------------------------------------------------------- #

def workflow_uses_print_flag(workflow_yaml: str) -> bool:
    """True if the workflow invokes ``claude`` with ``-p`` or ``--print``.

    This guards the Sample Question 10 fix: a CI job that runs bare
    ``claude "..."`` hangs waiting for interactive input. Only the ``-p`` /
    ``--print`` flag makes it non-interactive — an env var like
    ``CLAUDE_HEADLESS``, a ``--batch`` flag, or ``< /dev/null`` does not count.

    Scans every ``run:`` script for a ``claude`` command carrying the flag as a
    distinct token. Falls back to a token scan of the raw text if the YAML does
    not parse.
    """

    def _command_lines(text: str) -> list[str]:
        # Join backslash-newline continuations so multi-line commands are one line.
        joined = text.replace("\\\n", " ")
        return [ln.strip() for ln in joined.splitlines() if ln.strip()]

    def _line_has_print_flag(line: str) -> bool:
        try:
            tokens = shlex.split(line, comments=True)
        except ValueError:
            tokens = line.split()
        if "claude" not in tokens:
            return False
        return "-p" in tokens or "--print" in tokens

    run_scripts: list[str] = []
    try:
        doc = yaml.safe_load(workflow_yaml)
    except yaml.YAMLError:
        doc = None

    if isinstance(doc, dict):
        for job in (doc.get("jobs") or {}).values():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if isinstance(step, dict) and isinstance(step.get("run"), str):
                    run_scripts.append(step["run"])

    # Fall back to scanning the whole file if we could not extract structured runs.
    if not run_scripts:
        run_scripts = [workflow_yaml]

    for script in run_scripts:
        for line in _command_lines(script):
            if _line_has_print_flag(line):
                return True
    return False


# --------------------------------------------------------------------------- #
# CLI (uv run ci_review.py ...)
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

    schema = json.loads(open(args.schema, encoding="utf-8").read())
    findings = parse_findings(open(args.findings, encoding="utf-8").read(), schema)

    if args.prior:
        prior_doc = json.loads(open(args.prior, encoding="utf-8").read())
        prior = prior_doc["findings"] if isinstance(prior_doc, dict) else prior_doc
        findings = dedupe_against_prior(findings, prior)

    print(json.dumps(to_pr_comments(findings), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
