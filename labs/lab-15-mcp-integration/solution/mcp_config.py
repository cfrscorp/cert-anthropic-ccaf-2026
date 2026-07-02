"""Reference solution for L15 — MCP Server Integration into Claude Code.

Four helpers that model the mechanics behind Task Statement 2.4:

- ``expand_env``          resolve ``${VAR}`` references in an MCP config from an
                          environment mapping (raise on a missing variable).
- ``has_hardcoded_secret`` detect a literal credential baked into a config
                          instead of a ``${VAR}`` placeholder.
- ``merge_scopes``        combine project-scoped and user-scoped servers so the
                          agent sees BOTH sets simultaneously.
- ``improve_tool_description`` enrich a terse MCP tool description so the agent
                          prefers it over a built-in like Grep.

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

import re

__all__ = [
    "expand_env",
    "has_hardcoded_secret",
    "merge_scopes",
    "improve_tool_description",
]

# ${VAR} reference anywhere inside a string.
_VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
# A value that is *only* a placeholder (never counts as a hardcoded secret).
_PLACEHOLDER_ONLY = re.compile(r"^\s*\$\{[A-Za-z_][A-Za-z0-9_]*\}\s*$")
# Config keys that name a credential.
_SECRET_KEY = re.compile(r"(TOKEN|SECRET|API[_-]?KEY|KEY|PASSWORD|PASSWD|PAT|CREDENTIAL)", re.I)
# Value shapes that are unmistakably real credentials.
_SECRET_VALUE = re.compile(
    r"(ghp_|gho_|ghs_|github_pat_|sk-ant-|sk-|xox[baprs]-|glpat-|AKIA[0-9A-Z]{8}|AIza[0-9A-Za-z_\-]{10})"
)


def expand_env(config: dict, env: dict) -> dict:
    """Return a copy of ``config`` with every ``${VAR}`` replaced from ``env``.

    Walks the config recursively (dicts, lists, strings). A string may contain
    one or more ``${VAR}`` references and literal text around them.

    Raises:
        KeyError: if a referenced variable is absent from ``env``. The message
            is the missing variable name, so callers/tests can assert on it.
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
    """Return True if a literal credential appears instead of a ``${VAR}`` ref.

    Two signals count as a hardcoded secret:
      1. a value matching a known credential shape (e.g. ``ghp_...``), or
      2. a value under a credential-named key (``*_TOKEN``, ``*_SECRET``, ...)
         that is a non-empty literal rather than a pure ``${VAR}`` placeholder.

    Pure ``${VAR}`` placeholders never count — that is the pattern we want.
    """

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


def merge_scopes(project: dict, user: dict) -> dict:
    """Merge project-scoped and user-scoped MCP configs.

    Tools from every configured server are discovered at connection time and are
    available to the agent simultaneously, so the merged config must contain the
    servers from BOTH scopes under ``mcpServers``. On a name collision the
    project (shared, version-controlled) entry wins, matching Claude Code's
    precedence of project scope over user scope.
    """
    merged_servers: dict = {}
    merged_servers.update((user or {}).get("mcpServers", {}))
    merged_servers.update((project or {}).get("mcpServers", {}))  # project wins
    return {"mcpServers": merged_servers}


def improve_tool_description(desc: str) -> str:
    """Enrich a terse MCP tool description so the agent prefers it over Grep.

    A one-line description like "Search code." gives the model no reason to pick
    the MCP tool over the built-in Grep. The rewrite spells out capabilities,
    the structured output shape, and an explicit "Use this when ... not when ..."
    boundary that names Grep, so tool selection is driven by the description.
    """
    terse = desc.strip().rstrip(".")
    return (
        f"{terse}. "
        "Capabilities: runs an index-backed, ranked search across the connected "
        "repository and issue tracker, resolving symbols and cross-references — "
        "context the built-in Grep tool cannot recover from raw lines. "
        "Outputs: a JSON array of {path, line, snippet, symbol, score} matches "
        "ordered by relevance. "
        "Use this when you need ranked, context-rich results across the project "
        "or its issues; prefer it over the built-in Grep tool, which only returns "
        "unranked literal line matches with no symbol context. "
        "Not when you already know the exact file path (use Read) or only need a "
        "literal string count within a single known file."
    )
