"""Deterministic tests for L25 — Capstone: Claude Code Team & CI Workflow.

These pass against solution/ (LAB_TARGET=solution) and fail against an
unfinished starter/ (whose functions raise NotImplementedError). They exercise
the integrated configuration and the four public helpers:

    validate_project(root)  — [] for the well-formed active config, non-empty for
                              a deliberately broken fixture.
    rules_for_path(...)     — .test.tsx -> testing rule, src/api/* -> api rule.
    expand_env / has_hardcoded_secret — the token resolves and no secret is baked
                              into .mcp.json.
    the CI workflow         — contains -p/--print AND --json-schema.
    choose_mode(...)        — plan for the microservice task, direct for a
                              single-file fix.

Config artifacts are read from the ACTIVE target dir (starter/ or solution/) via
labkit.target_dir, so the starter's TODO stubs make these fail until completed.

Run from labs/:  uv run pytest lab-25-capstone-team-workflow
Validate ref:    LAB_TARGET=solution uv run pytest lab-25-capstone-team-workflow
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labkit import lab_module, lab_root, target_dir

vc = lab_module(__file__, "validate_config")

TARGET = target_dir(__file__)
BROKEN = lab_root(__file__) / "fixtures" / "broken"
WORKFLOW = TARGET / ".github" / "workflows" / "claude-ci.yml"
MCP_JSON = TARGET / ".mcp.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# validate_project — the integrative check
# --------------------------------------------------------------------------- #

def test_validate_project_accepts_the_active_config():
    problems = vc.validate_project(str(TARGET))
    assert problems == [], f"expected a well-formed config, got problems: {problems}"


def test_validate_project_flags_a_broken_config():
    problems = vc.validate_project(str(BROKEN))
    assert problems, "expected the broken fixture to report at least one problem"
    joined = " ".join(problems).lower()
    # The broken fixture trips several distinct checks.
    assert "import" in joined
    assert "paths" in joined
    assert "secret" in joined


# --------------------------------------------------------------------------- #
# rules_for_path — path-scoped rule routing (Task 3.3 / Sample Q6)
# --------------------------------------------------------------------------- #

def _load_rules() -> list[dict]:
    """Parse the active target's .claude/rules/*.md via the module under test."""
    rules_dir = TARGET / ".claude" / "rules"
    rules: list[dict] = []
    for md in sorted(rules_dir.glob("*.md")):
        fm = vc.parse_frontmatter(_read(md))
        rules.append({"name": md.stem, "paths": fm.get("paths", [])})
    return rules


def test_test_file_routes_to_testing_rule():
    rules = _load_rules()
    assert vc.rules_for_path("src/components/Button.test.tsx", rules) == ["testing"]


def test_api_file_routes_to_api_rule():
    rules = _load_rules()
    assert vc.rules_for_path("src/api/users.ts", rules) == ["api"]


def test_double_star_crosses_directories():
    rules = _load_rules()
    assert vc.rules_for_path("Widget.test.ts", rules) == ["testing"]
    assert vc.rules_for_path("a/b/c/Deep.test.tsx", rules) == ["testing"]
    assert vc.rules_for_path("src/api/v1/handlers.ts", rules) == ["api"]


def test_nonmatching_path_matches_nothing():
    rules = _load_rules()
    assert vc.rules_for_path("README.md", rules) == []


# --------------------------------------------------------------------------- #
# expand_env / has_hardcoded_secret — MCP credentials (Task 2.4)
# --------------------------------------------------------------------------- #

def test_mcp_json_has_no_hardcoded_secret():
    config = json.loads(_read(MCP_JSON))
    assert vc.has_hardcoded_secret(config) is False


def test_expand_env_resolves_the_token():
    config = json.loads(_read(MCP_JSON))
    env = {
        "GITHUB_TOKEN": "ghp_fromenv",
        "JIRA_BASE_URL": "https://example.atlassian.net",
        "JIRA_API_TOKEN": "jira_fromenv",
    }
    resolved = vc.expand_env(config, env)
    # After expansion, the ${GITHUB_TOKEN} placeholder is gone and the injected
    # value is present somewhere in the config.
    blob = json.dumps(resolved)
    assert "${GITHUB_TOKEN}" not in blob
    assert "ghp_fromenv" in blob


def test_expand_env_raises_on_missing_variable():
    with pytest.raises(KeyError):
        vc.expand_env({"env": {"TOKEN": "${GITHUB_TOKEN}"}}, {})


# --------------------------------------------------------------------------- #
# CI workflow — non-interactive + structured output (Task 3.6 / Sample Q10)
# --------------------------------------------------------------------------- #

def _workflow_noncomment_text() -> str:
    """The workflow YAML with `#` comment lines stripped.

    Comments (including TODO hints in the starter) can *mention* the flags; the
    real proof is the actual `claude` invocation, so we ignore comment lines.
    """
    lines = [ln for ln in _read(WORKFLOW).splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lines)


def test_ci_workflow_runs_noninteractive_with_schema():
    text = _workflow_noncomment_text()
    assert (" -p " in text) or ("--print" in text) or text.rstrip().endswith(" -p"), (
        "CI must invoke claude with -p/--print so it does not hang on input"
    )
    assert "--json-schema" in text, "CI must use --json-schema for structured output"


# --------------------------------------------------------------------------- #
# choose_mode — plan vs direct execution (Task 3.4 / Sample Q5)
# --------------------------------------------------------------------------- #

def test_microservice_restructuring_is_plan():
    task = {
        "multi_file_count": 60,
        "architectural": True,
        "multiple_valid_approaches": True,
        "clear_scope": False,
    }
    assert vc.choose_mode(task) == "plan"


def test_single_file_fix_is_direct():
    task = {
        "multi_file_count": 1,
        "architectural": False,
        "multiple_valid_approaches": False,
        "clear_scope": True,
    }
    assert vc.choose_mode(task) == "direct"
