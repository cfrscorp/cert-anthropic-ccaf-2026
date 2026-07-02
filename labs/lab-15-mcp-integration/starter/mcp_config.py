"""Starter scaffold for L15 — MCP Server Integration into Claude Code.

Implement the four functions below, then fix the config artifacts in this
directory (``.mcp.json``, ``user-claude.json``, ``resources.md``). Run:

    uv run pytest lab-15-mcp-integration      # from labs/

These helpers model the mechanics behind Task Statement 2.4: environment
variable expansion for secret-free configs, keeping credentials out of version
control, discovering tools from ALL configured servers simultaneously, and
writing tool descriptions the agent will actually prefer over built-ins.

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

__all__ = [
    "expand_env",
    "has_hardcoded_secret",
    "merge_scopes",
    "improve_tool_description",
]


def expand_env(config: dict, env: dict) -> dict:
    """Return a copy of ``config`` with every ``${VAR}`` replaced from ``env``.

    Walk the config recursively (dicts, lists, strings). A string may contain
    one or more ``${VAR}`` references plus literal text around them.

    Raise ``KeyError(name)`` if a referenced variable is missing from ``env`` so
    a misconfigured server fails loudly instead of connecting with a blank token.

    TODO: implement.
    """
    raise NotImplementedError("Implement expand_env")


def has_hardcoded_secret(config: dict) -> bool:
    """Return True if a literal credential appears instead of a ``${VAR}`` ref.

    Flag a value that matches a known credential shape (e.g. ``ghp_...``), or a
    non-empty literal under a credential-named key (``*_TOKEN``, ``*_SECRET``,
    ...). A pure ``${VAR}`` placeholder must NOT count — that is the safe pattern.

    TODO: implement.
    """
    raise NotImplementedError("Implement has_hardcoded_secret")


def merge_scopes(project: dict, user: dict) -> dict:
    """Merge project-scoped and user-scoped MCP configs.

    Tools from every configured server are available to the agent at once, so the
    result must include the servers from BOTH scopes under ``mcpServers``.
    Decide a precedence rule for name collisions (project scope wins).

    TODO: implement.
    """
    raise NotImplementedError("Implement merge_scopes")


def improve_tool_description(desc: str) -> str:
    """Enrich a terse MCP tool description so the agent prefers it over Grep.

    Spell out the tool's capabilities, its structured output shape, and an
    explicit "Use this when ... not when ..." boundary that names the built-in
    Grep tool, so tool selection is driven by the description.

    TODO: implement.
    """
    raise NotImplementedError("Implement improve_tool_description")
