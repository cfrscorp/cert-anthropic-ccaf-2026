"""Deterministic tests for Lab 07 — Rules, Commands & Skills.

These pass against solution/ (LAB_TARGET=solution) and fail against an
unfinished starter/. They exercise:

- parse_frontmatter extracting the `paths:` list from a .claude/rules file
- rules_for_path routing paths to the right rule (incl. ** across directories)
- validate_skill_frontmatter accepting a good SKILL.md and flagging a bad one
- the presence of the shared /review command in the active target's
  .claude/commands/ directory

Config files are read from the ACTIVE target dir (starter/ or solution/) via
labkit.target_dir, so the starter's TODO stubs make these tests fail until the
learner fills them in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from labkit import lab_module, target_dir

cc = lab_module(__file__, "claude_config")
TARGET = target_dir(__file__)
RULES_DIR = TARGET / ".claude" / "rules"
COMMANDS_DIR = TARGET / ".claude" / "commands"
SKILLS_DIR = TARGET / ".claude" / "skills"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_rules() -> list[dict]:
    """Parse every .claude/rules/*.md file in the active target into rule dicts."""
    rules: list[dict] = []
    for md in sorted(RULES_DIR.glob("*.md")):
        fm = cc.parse_frontmatter(_read(md))
        rules.append({"name": md.stem, "paths": fm.get("paths", [])})
    return rules


# --------------------------------------------------------------------------- #
# parse_frontmatter
# --------------------------------------------------------------------------- #

def test_parse_frontmatter_extracts_paths():
    fm = cc.parse_frontmatter(_read(RULES_DIR / "testing.md"))
    assert isinstance(fm, dict)
    assert "**/*.test.tsx" in fm["paths"]
    assert "**/*.test.ts" in fm["paths"]


def test_parse_frontmatter_no_frontmatter_returns_empty():
    assert cc.parse_frontmatter("# Just a heading\n\nno frontmatter here") == {}
    assert cc.parse_frontmatter("") == {}


# --------------------------------------------------------------------------- #
# rules_for_path
# --------------------------------------------------------------------------- #

def test_test_file_routes_to_testing_rule():
    rules = _load_rules()
    assert cc.rules_for_path("src/components/Button.test.tsx", rules) == ["testing"]


def test_api_file_routes_to_api_rule():
    rules = _load_rules()
    assert cc.rules_for_path("src/api/users.ts", rules) == ["api"]


def test_nonmatching_path_matches_nothing():
    rules = _load_rules()
    assert cc.rules_for_path("README.md", rules) == []
    assert cc.rules_for_path("src/components/Button.tsx", rules) == []


def test_double_star_matches_nested_directories():
    rules = _load_rules()
    # ** must cross directory boundaries in both directions:
    assert cc.rules_for_path("Widget.test.ts", rules) == ["testing"]  # top level
    assert cc.rules_for_path("a/b/c/Deep.test.tsx", rules) == ["testing"]  # deeply nested
    assert cc.rules_for_path("src/api/v1/handlers.ts", rules) == ["api"]  # nested api
    assert cc.rules_for_path("terraform/modules/vpc/main.tf", rules) == ["terraform"]


def test_glob_matcher_directly():
    # A single rule set, asserting the ** semantics without file IO.
    rules = [{"name": "tf", "paths": ["terraform/**/*"]}]
    assert cc.rules_for_path("terraform/main.tf", rules) == ["tf"]
    assert cc.rules_for_path("terraform/modules/vpc/outputs.tf", rules) == ["tf"]
    assert cc.rules_for_path("src/main.tf", rules) == []


# --------------------------------------------------------------------------- #
# validate_skill_frontmatter
# --------------------------------------------------------------------------- #

def test_valid_skill_frontmatter_accepted():
    fm = cc.parse_frontmatter(_read(SKILLS_DIR / "analyze-codebase" / "SKILL.md"))
    # Sanity: the reference skill declares the three key frontmatter options.
    assert fm.get("context") == "fork"
    assert "allowed-tools" in fm
    assert "argument-hint" in fm
    assert cc.validate_skill_frontmatter(fm) == []


def test_invalid_skill_frontmatter_flagged():
    bad = {
        "name": "broken",
        "context": "forked",          # wrong value
        "tools": "Read, Grep",        # unknown key
        # missing description
    }
    problems = cc.validate_skill_frontmatter(bad)
    assert problems, "expected validation problems for a bad SKILL.md"
    joined = " ".join(problems).lower()
    assert "description" in joined
    assert "context" in joined


def test_empty_allowed_tools_flagged():
    problems = cc.validate_skill_frontmatter(
        {"description": "x", "context": "fork", "allowed-tools": []}
    )
    assert any("allowed-tools" in p for p in problems)


# --------------------------------------------------------------------------- #
# project-scoped command presence
# --------------------------------------------------------------------------- #

def test_review_command_exists_in_project_commands_dir():
    review = COMMANDS_DIR / "review.md"
    assert review.exists(), (
        "team /review command must live in .claude/commands/ (project-scoped, "
        "version-controlled) so every developer gets it on clone/pull"
    )
    # It must carry a description in frontmatter to render as a slash command.
    fm = cc.parse_frontmatter(_read(review))
    assert fm.get("description"), "review command needs a `description` in frontmatter"
