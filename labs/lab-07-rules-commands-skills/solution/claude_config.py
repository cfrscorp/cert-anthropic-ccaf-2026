"""Reference solution: parsing and validating Claude Code configuration.

This module models the three project-scoped configuration mechanisms exercised
in Lab 07:

- ``.claude/rules/*.md``   — path-conditional convention files (YAML frontmatter
  with a ``paths:`` list of globs). Loaded only when editing a matching file.
- ``.claude/commands/*.md`` — project-scoped slash commands (shared via git).
- ``.claude/skills/<name>/SKILL.md`` — on-demand skills whose frontmatter may set
  ``context: fork``, ``allowed-tools``, and ``argument-hint``.

The public API is intentionally small and pure so the tests can exercise it
deterministically and offline:

    parse_frontmatter(markdown_text) -> dict
    rules_for_path(path, rules)      -> list[str]   (names of matching rules)
    validate_skill_frontmatter(fm)   -> list[str]   (problems; empty == valid)

No Claude calls, no filesystem coupling — callers read the files and pass the
text/dicts in.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

# Keys a SKILL.md frontmatter block is allowed to declare. Grounded in Task
# Statement 3.2: skills support `context: fork`, `allowed-tools`, and
# `argument-hint`, plus the usual `name`/`description` identity fields.
_ALLOWED_SKILL_KEYS = {"name", "description", "context", "allowed-tools", "argument-hint"}


def parse_frontmatter(markdown_text: str) -> dict:
    """Extract the leading YAML frontmatter block from a markdown document.

    Frontmatter is the block delimited by a line of ``---`` at the very top of
    the file and a closing ``---`` line. Returns the parsed mapping, or ``{}``
    when there is no frontmatter (or it is empty / not a mapping).
    """
    if not markdown_text:
        return {}
    # Tolerate a UTF-8 BOM and leading blank lines before the opening fence.
    text = markdown_text.lstrip("﻿")
    stripped = text.lstrip("\n")
    if not stripped.startswith("---"):
        return {}

    lines = stripped.splitlines()
    # lines[0] is the opening "---". Find the closing fence.
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing is None:
        return {}

    block = "\n".join(lines[1:closing])
    data = yaml.safe_load(block)
    if not isinstance(data, dict):
        return {}
    return data


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a glob (with ``**`` crossing directory boundaries) to a regex.

    Semantics:
      - ``**/``  matches zero or more path segments (so ``**/*.test.tsx`` matches
        both ``Button.test.tsx`` and ``src/ui/Button.test.tsx``).
      - ``**``   matches anything, including ``/``.
      - ``*``    matches anything except ``/`` (a single path segment).
      - ``?``    matches a single character except ``/``.
      - all other characters are matched literally.
    """
    i = 0
    out: list[str] = []
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i : i + 2] == "**":
                # Consume a trailing slash so "**/" collapses to zero-or-more dirs.
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
    """Return True if ``path`` matches the glob ``pattern`` (``**`` aware)."""
    # Normalize Windows-style separators so rules stay OS-agnostic.
    normalized = path.replace("\\", "/").lstrip("./")
    return _glob_to_regex(pattern).match(normalized) is not None


def rules_for_path(path: str, rules: list[dict]) -> list[str]:
    """Names of the rules whose ``paths`` globs match ``path``.

    Each rule is a mapping with a ``name`` and a ``paths`` list, e.g.::

        {"name": "testing", "paths": ["**/*.test.tsx", "**/*.test.ts"]}

    A rule matches if ANY of its globs matches the path. This mirrors how Claude
    Code decides which ``.claude/rules/*.md`` files to load for the file you are
    currently editing.
    """
    matched: list[str] = []
    for rule in rules:
        patterns = rule.get("paths") or []
        if isinstance(patterns, str):
            patterns = [patterns]
        if any(path_matches(path, p) for p in patterns):
            matched.append(rule.get("name", ""))
    return matched


def validate_skill_frontmatter(fm: dict) -> list[str]:
    """Validate a SKILL.md frontmatter mapping; return a list of problems.

    An empty list means the frontmatter is valid. Rules enforced:

      - ``description`` is required (skills advertise themselves by description).
      - only known keys are permitted (``name``, ``description``, ``context``,
        ``allowed-tools``, ``argument-hint``).
      - ``context``, when present, must be ``"fork"``.
      - ``allowed-tools``, when present, must be a non-empty list or a non-empty
        comma-separated string of tool names.
      - ``argument-hint``, when present, must be a non-empty string.
    """
    if not isinstance(fm, dict):
        return ["frontmatter is not a mapping"]

    problems: list[str] = []

    desc = fm.get("description")
    if not desc or not str(desc).strip():
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
            tools = None  # signal a type error
        if tools is None:
            problems.append("'allowed-tools' must be a list or comma-separated string")
        elif not tools:
            problems.append("'allowed-tools' is present but empty")

    if "argument-hint" in fm and not str(fm["argument-hint"]).strip():
        problems.append("'argument-hint' is present but empty")

    return problems
