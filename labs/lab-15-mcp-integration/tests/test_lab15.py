"""Deterministic tests for L15 — MCP Server Integration into Claude Code.

Runs against starter/ by default (learner's work) and solution/ when
LAB_TARGET=solution. All tests are offline and deterministic.
"""

from __future__ import annotations

import json

import pytest

from labkit import lab_module, target_dir

mc = lab_module(__file__, "mcp_config")
TARGET = target_dir(__file__)


# --------------------------------------------------------------------------- #
# Config artifacts
# --------------------------------------------------------------------------- #
def _load(name: str) -> dict:
    return json.loads((TARGET / name).read_text())


def test_project_mcp_json_parses_with_two_servers() -> None:
    cfg = _load(".mcp.json")
    servers = cfg["mcpServers"]
    assert len(servers) >= 2, "project .mcp.json should define at least two shared servers"
    assert "github" in servers, "expected a 'github' server in the project config"


def test_user_scoped_config_parses_with_a_personal_server() -> None:
    cfg = _load("user-claude.json")
    assert len(cfg.get("mcpServers", {})) >= 1, "user-claude.json needs a personal server"


def test_resources_md_documents_a_catalog() -> None:
    text = (TARGET / "resources.md").read_text().lower()
    assert "resource" in text and "catalog" in text
    assert "todo" not in text, "resources.md still contains a TODO stub"


# --------------------------------------------------------------------------- #
# expand_env
# --------------------------------------------------------------------------- #
def test_expand_env_resolves_github_token() -> None:
    cfg = {
        "mcpServers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
            }
        }
    }
    resolved = mc.expand_env(cfg, {"GITHUB_TOKEN": "ghp_live_value"})
    assert resolved["mcpServers"]["github"]["env"]["GITHUB_TOKEN"] == "ghp_live_value"
    # Original config must not be mutated.
    assert cfg["mcpServers"]["github"]["env"]["GITHUB_TOKEN"] == "${GITHUB_TOKEN}"


def test_expand_env_flags_missing_variable() -> None:
    cfg = {"env": {"TOKEN": "${MISSING_VAR}"}}
    with pytest.raises(KeyError):
        mc.expand_env(cfg, {})


# --------------------------------------------------------------------------- #
# has_hardcoded_secret
# --------------------------------------------------------------------------- #
def test_has_hardcoded_secret_flags_literal_token() -> None:
    cfg = {"mcpServers": {"github": {"env": {"GITHUB_TOKEN": "ghp_abcdef0123456789"}}}}
    assert mc.has_hardcoded_secret(cfg) is True


def test_has_hardcoded_secret_clears_placeholder_config() -> None:
    cfg = {"mcpServers": {"github": {"env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}}}}
    assert mc.has_hardcoded_secret(cfg) is False


def test_project_mcp_json_has_no_hardcoded_secret() -> None:
    assert mc.has_hardcoded_secret(_load(".mcp.json")) is False


# --------------------------------------------------------------------------- #
# merge_scopes
# --------------------------------------------------------------------------- #
def test_merge_scopes_exposes_both_scopes() -> None:
    project = {"mcpServers": {"github": {"command": "npx"}, "jira": {"command": "npx"}}}
    user = {"mcpServers": {"sqlite-scratch": {"command": "uvx"}}}
    merged = mc.merge_scopes(project, user)
    names = set(merged["mcpServers"])
    assert names == {"github", "jira", "sqlite-scratch"}


def test_merge_scopes_project_wins_on_collision() -> None:
    project = {"mcpServers": {"github": {"command": "project"}}}
    user = {"mcpServers": {"github": {"command": "user"}}}
    merged = mc.merge_scopes(project, user)
    assert merged["mcpServers"]["github"]["command"] == "project"


# --------------------------------------------------------------------------- #
# improve_tool_description
# --------------------------------------------------------------------------- #
def test_improve_tool_description_prefers_over_grep() -> None:
    terse = "Search code."
    improved = mc.improve_tool_description(terse)
    low = improved.lower()
    assert len(improved) > len(terse) * 3, "description should be substantially enriched"
    assert "grep" in low, "should name the built-in Grep tool it beats"
    assert "use this when" in low and "not when" in low, "needs an explicit boundary"
    assert "output" in low or "returns" in low, "should describe the output shape"
