"""Deterministic tests for Lab 02 — Claude Code Config Foundations.

Covered:
- CLAUDE.md hierarchy precedence (user < project < directory)   [Task 3.1]
- @import expansion, including relative-path resolution         [Task 3.1]
- user-level memory is not team-shared                          [Task 3.1]
- choose_tool for the canonical Task 2.5 cases                  [Task 2.5]

Run the learner's work (default):   uv run pytest lab-02-claude-code-config-foundations -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-02-claude-code-config-foundations -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

from labkit import lab_module

cfg = lab_module(__file__, "config_hierarchy")
tools = lab_module(__file__, "tool_selection")

SAMPLE = Path(__file__).resolve().parent.parent / "sample-project"


def _sample_files() -> dict[str, str]:
    """Build a {relative-posix-path: content} map from the sample-project tree."""
    files: dict[str, str] = {}
    for md in SAMPLE.rglob("*.md"):
        if md.name.endswith(".example.md"):
            continue  # illustrative user-level note, not part of the tree
        rel = md.relative_to(SAMPLE).as_posix()
        files[rel] = md.read_text()
    return files


# --------------------------------------------------------------------------- #
# Task 3.1 — hierarchy precedence
# --------------------------------------------------------------------------- #
def test_resolve_config_orders_least_to_most_specific() -> None:
    merged = cfg.resolve_config(
        {
            "directory": "DIR_RULE",
            "user": "USER_RULE",
            "project": "PROJECT_RULE",
        }
    )
    assert merged.index("USER_RULE") < merged.index("PROJECT_RULE") < merged.index("DIR_RULE")


def test_resolve_config_omits_missing_layers() -> None:
    merged = cfg.resolve_config({"project": "ONLY_PROJECT"})
    assert "ONLY_PROJECT" in merged
    assert "user memory" not in merged.lower()
    assert "directory memory" not in merged.lower()


def test_resolve_config_rejects_unknown_layer() -> None:
    with pytest.raises(ValueError):
        cfg.resolve_config({"global": "nope"})


# --------------------------------------------------------------------------- #
# Task 3.1 — user-level is not team-shared
# --------------------------------------------------------------------------- #
def test_user_layer_not_team_shared() -> None:
    assert cfg.is_team_shared("user") is False
    assert cfg.is_team_shared("project") is True
    assert cfg.is_team_shared("directory") is True


# --------------------------------------------------------------------------- #
# Task 3.1 — @import expansion
# --------------------------------------------------------------------------- #
def test_import_expands_and_removes_directive() -> None:
    files = _sample_files()
    assert "CLAUDE.md" in files, "sample-project root CLAUDE.md missing"
    expanded = cfg.resolve_imports("CLAUDE.md", files)
    # The @import line itself is gone...
    assert "@standards/testing.md" not in expanded
    # ...and the imported content is present.
    assert "Every module has a matching" in expanded


def test_import_resolves_relative_paths() -> None:
    files = _sample_files()
    api = "src/api/CLAUDE.md"
    assert api in files, "sample-project src/api/CLAUDE.md missing"
    expanded = cfg.resolve_imports(api, files)
    assert "@../../standards/testing.md" not in expanded
    assert "deterministic" in expanded.lower()


def test_import_synthetic_nested_chain() -> None:
    files = {
        "CLAUDE.md": "root\n@a/one.md\n",
        "a/one.md": "one\n@../b/two.md\n",
        "b/two.md": "two-leaf\n",
    }
    expanded = cfg.resolve_imports("CLAUDE.md", files)
    assert "root" in expanded and "one" in expanded and "two-leaf" in expanded
    assert "@" not in expanded


def test_missing_import_raises() -> None:
    files = {"CLAUDE.md": "@does/not/exist.md\n"}
    with pytest.raises(FileNotFoundError):
        cfg.resolve_imports("CLAUDE.md", files)


# --------------------------------------------------------------------------- #
# Task 2.5 — built-in tool selection
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "task, expected",
    [
        ("find all callers of a function", "Grep"),
        ("locate the error message string in the codebase", "Grep"),
        ("search for every import statement of requests", "Grep"),
        ("find files matching **/*.test.tsx", "Glob"),
        ("list files by extension across the repo", "Glob"),
        ("modify a unique line in config.py", "Edit"),
        ("Edit failed, no unique anchor text to match", "Write"),
        ("create a new file for the module", "Write"),
        ("run the test suite", "Bash"),
        ("read the full file contents of main.py", "Read"),
    ],
)
def test_choose_tool_canonical_cases(task: str, expected: str) -> None:
    assert tools.choose_tool(task) == expected


def test_choose_tool_return_is_valid() -> None:
    result = tools.choose_tool("find all callers of a function")
    assert result in tools.VALID_TOOLS


def test_choose_tool_unrecognized_raises() -> None:
    with pytest.raises(ValueError):
        tools.choose_tool("xyzzy plugh nothing relevant here")
