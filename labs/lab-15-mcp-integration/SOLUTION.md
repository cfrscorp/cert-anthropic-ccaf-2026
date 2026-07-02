# Lab 15 — Reference Solution

## Approach

Task Statement 2.4 is really four decisions, each mirrored by one artifact:

| 2.4 skill | Artifact / function |
|---|---|
| Shared vs personal scoping | `solution/.mcp.json` (project) + `solution/user-claude.json` (user) |
| Secret-free credentials via env expansion | `${GITHUB_TOKEN}` in `.mcp.json`; `expand_env`, `has_hardcoded_secret` |
| All servers available simultaneously | `merge_scopes` |
| Content catalogs as resources | `solution/resources.md` |
| Community over custom; descriptions beat Grep | Jira server in `.mcp.json`; `improve_tool_description` |

The Python module makes the config *mechanics* testable offline; the JSON and
Markdown artifacts are what you would actually commit (or deliberately not
commit, in the user-scope case).

## Key decisions & why

**Project scope vs user scope.** `.mcp.json` lives at the repo root and is
committed, so a teammate who clones the repo inherits GitHub and Jira with zero
setup — that is the point of *shared team tooling*. Personal or experimental
servers go in `~/.claude.json` (modeled by `user-claude.json`): user scope is
**not** version-controlled, so trying out a scratch SQLite server never leaks
into a teammate's session. Putting a personal server in `.mcp.json` (or, worse,
putting shared tooling only in user scope so new hires silently lack it) is the
classic scoping mistake — the mirror image of the CLAUDE.md hierarchy bug in L02.

**Environment-variable expansion for secrets.** `.mcp.json` is committed, so it
must be secret-free. `"GITHUB_TOKEN": "${GITHUB_TOKEN}"` keeps the *reference* in
the repo and the *value* in each developer's environment; Claude Code expands it
at launch. `has_hardcoded_secret` encodes the rule so "no secret is committed"
becomes a test assertion rather than a code-review hope: a pure `${VAR}` value is
fine, a literal `ghp_...` or any non-empty literal under a `*_TOKEN`/`*_SECRET`
key is flagged. `expand_env` raises `KeyError` on a missing variable so a broken
config fails loudly instead of connecting with a blank token.

**All servers discovered at connection time.** There is no "current" server to
switch to — every configured server's tools are live at once. `merge_scopes`
models exactly that: the union of project and user `mcpServers`. Project wins on
a name collision because shared, reviewed configuration should take precedence
over a personal override.

**Resources vs tools.** A tool is an action to invoke; a resource is content to
read. Exposing a **catalog** (open-issue summaries, a docs tree, a DB schema) as
a resource lets the agent see what exists in one read instead of guessing filters
across several `search_*` tool calls — fewer round trips, less context burned.
`resources.md` walks through the Jira issue-summary catalog and the before/after
call pattern.

**Community over custom, and descriptions that beat Grep.** Jira is a standard
integration, so we wire the maintained community server rather than hand-rolling
one; custom servers are reserved for genuinely team-specific workflows. And a
capable MCP search tool is worthless if the model keeps falling back to Grep —
`improve_tool_description` adds the capabilities, the structured output shape, and
a `Use this when ... not when ...` boundary that explicitly names Grep, so the
model has a reason to choose the MCP tool (the same description-first principle as
L05, applied to the built-in-vs-MCP contest).

## Reference walkthrough

- `expand_env` recurses over dict/list/str and `re.sub`s each `${VAR}`; a missing
  key raises `KeyError(name)`. It builds new containers, so the input is never
  mutated (the test asserts this).
- `has_hardcoded_secret` walks the config carrying each value's key. A pure
  `${VAR}` value short-circuits to `False`; a known credential shape
  (`ghp_`, `github_pat_`, `sk-ant-`, `glpat-`, `AKIA...`, ...) or a non-empty
  literal under a credential-named key returns `True`.
- `merge_scopes` unions `user` then `project` into `mcpServers` (so project
  overwrites on collision) and returns `{"mcpServers": ...}`.
- `improve_tool_description` keeps the terse text as a lead, then appends
  Capabilities / Outputs / a Grep-naming boundary.
- `solution/.mcp.json` — two shared servers (`github`, `jira`), each credential a
  `${VAR}` reference, no literals. `solution/user-claude.json` — one personal
  `sqlite-scratch` server. `solution/resources.md` — the catalog write-up.

## Common mistakes

- **Hardcoding the token** in `.mcp.json` instead of `${GITHUB_TOKEN}`. Committed
  secrets are the failure this task exists to prevent; `has_hardcoded_secret`
  catches it.
- **Wrong scope.** Shared tooling stranded in user scope (new teammates lack it)
  or a personal experiment committed in project scope (forced on everyone).
- **Assuming you must pick one server.** All configured servers' tools are live
  simultaneously; `merge_scopes` returns the union, not a choice.
- **Renaming a description without giving the model a reason.** A terse "Search
  code." loses to Grep. The rewrite must state capabilities, outputs, and an
  explicit boundary that names Grep.
- **Building a custom Jira server.** For standard integrations, prefer the
  community server; custom is for team-specific workflows.
- **Confusing resources with tools.** A catalog is content to *read* (a
  resource), not another action to *invoke* (a tool); that is what saves the
  exploratory calls.

## Checklist

- [ ] `expand_env` resolves `${GITHUB_TOKEN}`, raises `KeyError` on a missing var,
      and does not mutate its input.
- [ ] `has_hardcoded_secret` is `True` for a literal token, `False` for a `${VAR}`
      placeholder config.
- [ ] `merge_scopes` returns every server from both scopes; project wins on
      collision.
- [ ] `improve_tool_description` is substantially longer, names Grep, describes
      output, and has a `Use this when ... not when ...` boundary.
- [ ] `.mcp.json` has two shared servers, uses `${GITHUB_TOKEN}`, and contains no
      hardcoded secret.
- [ ] `user-claude.json` has one personal/experimental server.
- [ ] `resources.md` documents an MCP resource content catalog (no TODO left).
- [ ] `LAB_TARGET=solution uv run pytest lab-15-mcp-integration -q` is green; the
      default (starter) run fails until the work is complete.
