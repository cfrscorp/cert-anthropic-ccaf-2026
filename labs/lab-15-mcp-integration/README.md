# Lab 15 — MCP Server Integration into Claude Code

| | |
|---|---|
| **Domain** | 2 — Tool Design & MCP Integration |
| **Task statement** | 2.4 — Integrate MCP servers into Claude Code and agent workflows |
| **Difficulty** | 5 / 10 |
| **Estimated time** | 1:45 |
| **Prerequisites** | L02, L05 |

## Objective

Wire external capabilities into Claude Code through the Model Context Protocol
(MCP), the way a real team would. You will practice the four skills under Task
Statement 2.4:

1. **Scope servers correctly** — shared team tooling in a project-level
   `.mcp.json` (committed) vs personal/experimental servers in a user-level
   `~/.claude.json` (never committed).
2. **Keep secrets out of version control** with `${VAR}` environment-variable
   expansion in `.mcp.json` (e.g. `${GITHUB_TOKEN}`).
3. **Expose a content catalog as an MCP resource** so the agent gains visibility
   into available data without burning exploratory tool calls.
4. **Write MCP tool descriptions the agent will prefer over built-ins** like
   Grep, and **choose a community server over a custom one** for a standard
   integration (Jira).

## Background

When Claude Code starts, it reads MCP configuration from multiple scopes and
connects to every configured server. **Tools from all servers are discovered at
connection time and are available to the agent simultaneously** — there is no
"active server" to switch between.

Two scopes matter here:

- **Project scope — `.mcp.json`** at the repo root. Committed to version
  control, so every teammate who checks out the repo gets the same servers. This
  is where **shared team tooling** belongs (GitHub, Jira, the team database).
- **User scope — `~/.claude.json`**. Applies only to that developer and is
  **not** shared. This is where **personal or experimental** servers belong, so
  you can try a server without forcing it on the team.

Because `.mcp.json` is committed, it must contain **no secrets**. Instead of
pasting a token, you reference an environment variable — `"${GITHUB_TOKEN}"` —
which Claude Code expands from the developer's environment at launch. The repo
stays secret-free; each developer supplies their own token.

Two more ideas from 2.4:

- **Resources vs tools.** A *tool* is an action the agent invokes; a *resource*
  is addressable content it can read. Publishing a **content catalog** (issue
  summaries, a docs hierarchy, a DB schema) as a resource lets the agent see
  what exists up front instead of probing with repeated tool calls.
- **Community over custom.** For a standard integration like **Jira**, prefer a
  maintained community MCP server over writing your own; reserve custom servers
  for genuinely team-specific workflows.

This lab abstracts the config mechanics into a small Python module so the
behaviour is testable offline, and pairs it with the real config artifacts
(`.mcp.json`, `user-claude.json`, `resources.md`) you would ship.

## Tasks

Work in `starter/`. Each function raises `NotImplementedError` until you
implement it; keep the same public API.

1. **`expand_env(config, env) -> dict`** — return a copy of `config` with every
   `${VAR}` reference replaced from the `env` mapping (recurse through dicts,
   lists, and strings). Raise `KeyError(name)` if a referenced variable is
   missing, so a misconfigured server fails loudly rather than connecting with a
   blank credential. Do not mutate the input.

2. **`has_hardcoded_secret(config) -> bool`** — return `True` when a literal
   credential is baked in (a known token shape like `ghp_...`, or a non-empty
   literal under a credential-named key such as `*_TOKEN`/`*_SECRET`). A pure
   `${VAR}` placeholder must return `False` — that is the pattern we want.

3. **`merge_scopes(project, user) -> dict`** — return a config whose
   `mcpServers` contains the servers from **both** scopes, reflecting that all
   servers are available simultaneously. On a name collision, project scope wins.

4. **`improve_tool_description(desc) -> str`** — enrich a terse description so
   the agent prefers this MCP tool over the built-in Grep: describe its
   capabilities, its structured output, and an explicit
   `Use this when ... not when ...` boundary that names Grep.

5. **Fix the config artifacts** in `starter/`:
   - `.mcp.json` — replace the hardcoded token with `${GITHUB_TOKEN}` and add a
     **second** shared server (a community Jira server). No secrets committed.
   - `user-claude.json` — add one personal/experimental server (user scope).
   - `resources.md` — document one MCP resource content-catalog example.

## Deliverables

- `starter/mcp_config.py` with the four functions implemented.
- `starter/.mcp.json` — project-scoped, two servers, `${GITHUB_TOKEN}` expansion,
  no hardcoded secret.
- `starter/user-claude.json` — a user-scoped personal server.
- `starter/resources.md` — an MCP resource content-catalog write-up.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-15-mcp-integration
```

All tests should pass once the functions and config artifacts are complete.
Until then the default (starter) run fails. To validate the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-15-mcp-integration -q
```

## Stretch Goals

- **Enhanced tool description in the config.** Add a `github` search tool stub to
  `.mcp.json`-adjacent notes and write its description with
  `improve_tool_description`, then argue why the agent now prefers it over Grep
  for searching issues.
- **More resources.** Extend `resources.md` with a documentation-hierarchy
  resource (`docs://catalog/tree`) and a database-schema resource
  (`db://catalog/schema`), and estimate the exploratory tool calls each saves.
- **Precedence edge cases.** What should happen if the same server name appears
  in project and user scope with *different commands*? Justify your `merge_scopes`
  rule and note how you would surface the shadowing to the developer.
- **Custom vs community.** Identify one workflow in your own team that *would*
  justify a custom MCP server, and explain what makes it team-specific enough to
  not be served by a community server.
