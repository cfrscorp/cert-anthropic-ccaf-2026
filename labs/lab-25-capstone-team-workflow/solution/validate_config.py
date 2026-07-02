#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""Reference solution for L25 — Capstone: Claude Code Team & CI Workflow.

This module is the "auditor" for a team's project-scoped Claude Code
configuration. It rolls together the mechanics practised in the prerequisite
labs into one integrative validator plus the three judgment/plumbing helpers the
capstone re-implements from scratch (self-contained — nothing is imported from
other labs):

    validate_project(root)      -> list[str]   problems; [] means well-formed
    rules_for_path(path, rules) -> list[str]   names of matching path rules (L07)
    expand_env(config, env)     -> dict        resolve ${VAR} in .mcp.json  (L15)
    choose_mode(task)           -> "plan"|"direct"  plan-vs-direct call    (L08)

Supporting public helpers used by the validator and the tests:

    parse_frontmatter(text)         -> dict
    load_rules(root)                -> list[dict]  ({"name", "paths"} per rule)
    validate_skill_frontmatter(fm)  -> list[str]
    has_hardcoded_secret(config)    -> bool

``validate_project`` inspects a project's ``.claude/`` tree and CI workflow and
returns a list of problems (empty == the configuration is well-formed):

  1. ``.claude/CLAUDE.md`` is present (project-level universal standards).
  2. every ``@import`` in CLAUDE.md resolves to a file on disk.
  3. every ``.claude/rules/*.md`` declares a non-empty ``paths:`` glob list.
  4. the team ``/review`` command lives in ``.claude/commands/`` with a
     ``description`` (Sample Question 4).
  5. every ``.claude/skills/*/SKILL.md`` has valid frontmatter
     (``context: fork`` when present, ``allowed-tools``, ``argument-hint``).
  6. ``.mcp.json`` contains no hardcoded secret (uses ``${VAR}`` expansion).
  7. the CI workflow runs ``claude`` with ``-p``/``--print`` and ``--json-schema``
     (Sample Question 10 / Task Statement 3.6).

Because it is invoked from a shell as well as imported by the tests, it follows
the project script conventions (PEP 723 metadata, ``argparse`` with an Examples
epilog, ``__version__`` / ``--version``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

__version__ = "1.0.0"

__all__ = [
    "validate_project",
    "rules_for_path",
    "expand_env",
    "choose_mode",
    "parse_frontmatter",
    "load_rules",
    "validate_skill_frontmatter",
    "has_hardcoded_secret",
]

# --------------------------------------------------------------------------- #
# Frontmatter + glob matching (L07 semantics, re-implemented here)
# --------------------------------------------------------------------------- #

_ALLOWED_SKILL_KEYS = {"name", "description", "context", "allowed-tools", "argument-hint"}


def parse_frontmatter(markdown_text: str) -> dict:
    """Extract the leading ``---`` YAML frontmatter block; ``{}`` if none/invalid."""
    if not markdown_text:
        return {}
    text = markdown_text.lstrip("﻿")
    stripped = text.lstrip("\n")
    if not stripped.startswith("---"):
        return {}
    lines = stripped.splitlines()
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing is None:
        return {}
    data = yaml.safe_load("\n".join(lines[1:closing]))
    return data if isinstance(data, dict) else {}


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a glob (``**`` crosses directories) to an anchored regex."""
    i, n, out = 0, len(pattern), []
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i : i + 2] == "**":
                if pattern[i : i + 3] == "**/":
                    out.append(r"(?:.*/)?")
                    i += 3
                    continue
                out.append(r".*")
                i += 2
                continue
            out.append(r"[^/]*")
            i += 1
        elif c == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def path_matches(path: str, pattern: str) -> bool:
    """True if ``path`` matches the ``**``-aware glob ``pattern``."""
    normalized = path.replace("\\", "/").lstrip("./")
    return _glob_to_regex(pattern).match(normalized) is not None


def rules_for_path(path: str, rules: list[dict]) -> list[str]:
    """Names of the rules whose ``paths`` globs match ``path`` (L07 Task 3.3).

    Each rule is ``{"name": ..., "paths": [glob, ...]}``. A rule matches when ANY
    of its globs matches. This mirrors how Claude Code decides which
    ``.claude/rules/*.md`` files to load for the file being edited.
    """
    matched: list[str] = []
    for rule in rules:
        patterns = rule.get("paths") or []
        if isinstance(patterns, str):
            patterns = [patterns]
        if any(path_matches(path, p) for p in patterns):
            matched.append(rule.get("name", ""))
    return matched


def load_rules(root: str | Path) -> list[dict]:
    """Parse every ``<root>/.claude/rules/*.md`` into ``{"name", "paths"}`` dicts."""
    rules_dir = Path(root) / ".claude" / "rules"
    rules: list[dict] = []
    if not rules_dir.is_dir():
        return rules
    for md in sorted(rules_dir.glob("*.md")):
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        rules.append({"name": md.stem, "paths": fm.get("paths", [])})
    return rules


def validate_skill_frontmatter(fm: dict) -> list[str]:
    """Validate a SKILL.md frontmatter mapping; ``[]`` means valid (L07 Task 3.2)."""
    if not isinstance(fm, dict):
        return ["frontmatter is not a mapping"]
    problems: list[str] = []
    if not str(fm.get("description", "")).strip():
        problems.append("missing required 'description'")
    for key in fm:
        if key not in _ALLOWED_SKILL_KEYS:
            problems.append(f"unknown frontmatter key: {key!r}")
    if "context" in fm and fm["context"] != "fork":
        problems.append(f"invalid 'context': {fm['context']!r} (expected 'fork')")
    if "allowed-tools" in fm:
        at: Any = fm["allowed-tools"]
        if isinstance(at, str):
            tools = [t.strip() for t in at.split(",") if t.strip()]
        elif isinstance(at, list):
            tools = [str(t).strip() for t in at if str(t).strip()]
        else:
            tools = None
        if tools is None:
            problems.append("'allowed-tools' must be a list or comma-separated string")
        elif not tools:
            problems.append("'allowed-tools' is present but empty")
    if "argument-hint" in fm and not str(fm["argument-hint"]).strip():
        problems.append("'argument-hint' is present but empty")
    return problems


# --------------------------------------------------------------------------- #
# MCP env expansion + secret detection (L15 semantics, re-implemented here)
# --------------------------------------------------------------------------- #

_VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_PLACEHOLDER_ONLY = re.compile(r"^\s*\$\{[A-Za-z_][A-Za-z0-9_]*\}\s*$")
_SECRET_KEY = re.compile(
    r"(TOKEN|SECRET|API[_-]?KEY|KEY|PASSWORD|PASSWD|PAT|CREDENTIAL)", re.I
)
_SECRET_VALUE = re.compile(
    r"(ghp_|gho_|ghs_|github_pat_|sk-ant-|sk-|xox[baprs]-|glpat-|"
    r"AKIA[0-9A-Z]{8}|AIza[0-9A-Za-z_\-]{10})"
)


def expand_env(config: dict, env: dict) -> dict:
    """Return ``config`` with every ``${VAR}`` replaced from ``env`` (L15 Task 2.4).

    Recurses through dicts, lists, and strings. Raises ``KeyError(name)`` when a
    referenced variable is absent from ``env``, so credentials are never
    committed — they must resolve from the environment at run time.
    """

    def _resolve(value):
        if isinstance(value, dict):
            return {k: _resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_resolve(v) for v in value]
        if isinstance(value, str):
            def _sub(match: re.Match) -> str:
                name = match.group(1)
                if name not in env:
                    raise KeyError(name)
                return str(env[name])

            return _VAR_REF.sub(_sub, value)
        return value

    return _resolve(config)


def has_hardcoded_secret(config: dict) -> bool:
    """True if a literal credential appears instead of a ``${VAR}`` reference."""

    def _walk(value, key: str | None = None) -> bool:
        if isinstance(value, dict):
            return any(_walk(v, k) for k, v in value.items())
        if isinstance(value, list):
            return any(_walk(item, key) for item in value)
        if isinstance(value, str):
            if _PLACEHOLDER_ONLY.match(value):
                return False
            if _SECRET_VALUE.search(value):
                return True
            if key and _SECRET_KEY.search(key) and value.strip():
                return True
        return False

    return _walk(config)


# --------------------------------------------------------------------------- #
# Plan vs direct execution (L08 semantics, re-implemented here)
# --------------------------------------------------------------------------- #

def choose_mode(task: dict[str, Any]) -> str:
    """Return ``"plan"`` or ``"direct"`` for a task (Task Statement 3.4).

    Choose **plan** if ANY plan trigger is present: the change is architectural,
    has multiple valid approaches, touches more than one file, or has unclear
    scope. Otherwise the change is simple and well-scoped → **direct**.

    Sample Question 5: a monolith→microservices restructuring is architectural,
    multi-file, and multi-approach — its complexity is stated up front, so you
    enter plan mode rather than switching later. A single-file bug fix with a
    clear stack trace has none of these triggers → direct execution.
    """
    architectural = bool(task.get("architectural", False))
    multiple_valid_approaches = bool(task.get("multiple_valid_approaches", False))
    multi_file = int(task.get("multi_file_count", 1)) > 1
    clear_scope = bool(task.get("clear_scope", True))
    if architectural or multiple_valid_approaches or multi_file or not clear_scope:
        return "plan"
    return "direct"


# --------------------------------------------------------------------------- #
# The capstone validator
# --------------------------------------------------------------------------- #

_IMPORT_REF = re.compile(r"(?m)^\s*@(\S+)")


def _resolve_imports(claude_md: Path) -> list[str]:
    """Return unresolved ``@import`` targets referenced by ``claude_md``."""
    text = claude_md.read_text(encoding="utf-8")
    problems: list[str] = []
    for ref in _IMPORT_REF.findall(text):
        target = (claude_md.parent / ref).resolve()
        if not target.is_file():
            problems.append(f"@import target does not resolve: {ref}")
    return problems


def validate_project(root: str) -> list[str]:
    """Audit a project's Claude Code config; return problems ([] == well-formed).

    See the module docstring for the seven checks. ``root`` is the project
    directory that contains ``.claude/``, ``.mcp.json``, and ``.github/``.
    """
    base = Path(root)
    problems: list[str] = []

    # 1. project-level CLAUDE.md present.
    claude_md = base / ".claude" / "CLAUDE.md"
    if not claude_md.is_file():
        problems.append("missing project-level .claude/CLAUDE.md")
    else:
        # 2. every @import resolves.
        problems.extend(_resolve_imports(claude_md))

    # 3. every rule declares a non-empty paths glob list.
    rules_dir = base / ".claude" / "rules"
    if not rules_dir.is_dir():
        problems.append("missing .claude/rules/ directory")
    else:
        rule_files = sorted(rules_dir.glob("*.md"))
        if not rule_files:
            problems.append(".claude/rules/ has no rule files")
        for md in rule_files:
            fm = parse_frontmatter(md.read_text(encoding="utf-8"))
            paths = fm.get("paths")
            if not paths or not isinstance(paths, list):
                problems.append(f"rule {md.name} is missing a non-empty 'paths' glob list")

    # 4. team /review command in .claude/commands/ with a description.
    review = base / ".claude" / "commands" / "review.md"
    if not review.is_file():
        problems.append("missing team command .claude/commands/review.md")
    else:
        fm = parse_frontmatter(review.read_text(encoding="utf-8"))
        if not str(fm.get("description", "")).strip():
            problems.append("review command needs a 'description' in frontmatter")

    # 5. every SKILL.md has valid frontmatter.
    skills_dir = base / ".claude" / "skills"
    skill_files = sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []
    if not skill_files:
        problems.append("missing .claude/skills/<name>/SKILL.md")
    for sk in skill_files:
        fm = parse_frontmatter(sk.read_text(encoding="utf-8"))
        for p in validate_skill_frontmatter(fm):
            problems.append(f"skill {sk.parent.name}: {p}")

    # 6. .mcp.json exists and has no hardcoded secret.
    mcp = base / ".mcp.json"
    if not mcp.is_file():
        problems.append("missing .mcp.json")
    else:
        try:
            config = json.loads(mcp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f".mcp.json is not valid JSON: {exc}")
        else:
            if has_hardcoded_secret(config):
                problems.append(".mcp.json contains a hardcoded secret (use ${VAR} expansion)")

    # 7. CI workflow uses -p/--print and --json-schema.
    workflow = base / ".github" / "workflows" / "claude-ci.yml"
    if not workflow.is_file():
        problems.append("missing .github/workflows/claude-ci.yml")
    else:
        text = workflow.read_text(encoding="utf-8")
        if not re.search(r"(?<![-\w])(-p|--print)(?![-\w])", text):
            problems.append("CI workflow does not run claude with -p/--print (would hang on input)")
        if "--json-schema" not in text:
            problems.append("CI workflow does not use --json-schema for structured output")

    return problems


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_config.py",
        description=(
            "Audit a team's project-scoped Claude Code configuration "
            "(.claude/, .mcp.json, .github/workflows/) and report problems. "
            "Exits 0 when the configuration is well-formed, 1 otherwise."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Audit the reference configuration in this lab\n"
            "  uv run validate_config.py solution\n\n"
            "  # Audit your own work in the starter tree\n"
            "  uv run validate_config.py starter\n\n"
            "  # Audit the current project (looks for ./.claude etc.)\n"
            "  uv run validate_config.py .\n\n"
            "  # Print the version\n"
            "  uv run validate_config.py --version\n"
        ),
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root that contains .claude/, .mcp.json, and .github/ (default: .).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    problems = validate_project(args.root)
    if not problems:
        print(f"OK: {args.root} — configuration is well-formed.")
        return 0
    print(f"FAIL: {args.root} — {len(problems)} problem(s):")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
