#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""Starter for L25 — Capstone: Claude Code Team & CI Workflow.

Implement the four public functions below (plus any helpers you need). They are
self-contained: do NOT import from other labs — re-implement the semantics here.

    validate_project(root)      -> list[str]   problems; [] means well-formed
    rules_for_path(path, rules) -> list[str]   names of matching path rules (L07)
    expand_env(config, env)     -> dict        resolve ${VAR} in .mcp.json  (L15)
    choose_mode(task)           -> "plan"|"direct"  plan-vs-direct call    (L08)

``validate_project(root)`` inspects a project directory that contains
``.claude/``, ``.mcp.json`` and ``.github/`` and returns a list of problem
strings (empty == the configuration is well-formed). Check ALL of:

  1. ``.claude/CLAUDE.md`` is present.
  2. every ``@import`` in CLAUDE.md resolves to a file on disk (resolve the path
     relative to CLAUDE.md's own directory).
  3. every ``.claude/rules/*.md`` declares a non-empty ``paths:`` glob list.
  4. ``.claude/commands/review.md`` exists and has a ``description`` in its
     frontmatter (project-scoped, version-controlled — Sample Question 4).
  5. every ``.claude/skills/*/SKILL.md`` has valid frontmatter
     (``context`` must be ``fork`` when present; ``allowed-tools`` and
     ``argument-hint`` non-empty when present).
  6. ``.mcp.json`` contains no hardcoded secret (uses ``${VAR}`` expansion).
  7. ``.github/workflows/claude-ci.yml`` runs ``claude`` with ``-p``/``--print``
     AND ``--json-schema`` (Sample Question 10 / Task Statement 3.6).

pyyaml is available (``import yaml``) for parsing frontmatter; ``json`` for
``.mcp.json``. Follow the project script conventions if you wire up a CLI:
PEP 723 metadata (already present), argparse ``-h`` with an Examples epilog,
``__version__`` and a ``--version`` action.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-25-capstone-team-workflow -q
"""

from __future__ import annotations

from typing import Any

# You will likely want these:
# import json
# import re
# from pathlib import Path
# import yaml

__version__ = "0.0.0"


def rules_for_path(path: str, rules: list[dict]) -> list[str]:
    """Names of the rules whose ``paths`` globs match ``path`` (L07 Task 3.3).

    Each rule is ``{"name": ..., "paths": [glob, ...]}``. A rule matches when ANY
    of its globs matches. Your matcher MUST handle ``**`` crossing directory
    boundaries: ``**/*.test.tsx`` matches both ``Button.test.tsx`` and
    ``src/ui/Button.test.tsx``; ``src/api/**/*`` matches ``src/api/users.ts`` and
    ``src/api/v1/handlers.ts``. Plain ``fnmatch`` is not enough.
    """
    raise NotImplementedError("TODO: implement rules_for_path()")


def expand_env(config: dict, env: dict) -> dict:
    """Return ``config`` with every ``${VAR}`` replaced from ``env`` (L15 Task 2.4).

    Recurse through dicts, lists, and strings. Raise ``KeyError(name)`` when a
    referenced variable is absent from ``env`` (credentials must resolve from the
    environment, never be committed).
    """
    raise NotImplementedError("TODO: implement expand_env()")


def has_hardcoded_secret(config: dict) -> bool:
    """True if a literal credential appears instead of a ``${VAR}`` reference.

    A pure ``${VAR}`` placeholder never counts. A value shaped like a known
    credential (e.g. ``ghp_...``, ``sk-ant-...``) counts, as does a non-empty
    literal under a credential-named key (``*_TOKEN``, ``*_SECRET``, ...).
    """
    raise NotImplementedError("TODO: implement has_hardcoded_secret()")


def choose_mode(task: dict[str, Any]) -> str:
    """Return ``"plan"`` or ``"direct"`` for a task (Task Statement 3.4).

    Choose **plan** if ANY plan trigger is present: ``architectural`` is True,
    ``multiple_valid_approaches`` is True, the change is multi-file
    (``multi_file_count > 1``), or scope is unclear (``clear_scope`` is False).
    Otherwise return **direct**.
    """
    raise NotImplementedError("TODO: implement choose_mode()")


def validate_project(root: str) -> list[str]:
    """Audit a project's Claude Code config; return problems ([] == well-formed).

    Implement the seven checks listed in the module docstring. ``root`` is the
    project directory containing ``.claude/``, ``.mcp.json`` and ``.github/``.
    """
    raise NotImplementedError("TODO: implement validate_project()")
