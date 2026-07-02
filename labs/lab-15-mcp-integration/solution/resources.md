# MCP resource: content catalog example

**Task Statement 2.4** calls out MCP *resources* as a mechanism for exposing
**content catalogs** (issue summaries, documentation hierarchies, database
schemas) so an agent gains visibility into available data **without spending
exploratory tool calls** to discover it.

A **tool** is an action the agent *invokes* ("search issues", "run query"). A
**resource** is addressable *content* the agent can *read* — the server
advertises it up front, so the agent starts already knowing what exists instead
of probing.

## Example: the Jira server exposes an issue-summary catalog

Instead of the agent calling a `search_issues` tool several times just to learn
what the backlog looks like, the `jira` server publishes a resource catalog:

| URI                              | Name                     | mimeType           | Description                                             |
|----------------------------------|--------------------------|--------------------|--------------------------------------------------------|
| `jira://catalog/open-issues`     | Open issues summary      | `application/json` | One line per open issue: key, title, status, assignee. |
| `jira://catalog/components`      | Component map            | `application/json` | Components and their lead + description.               |
| `jira://catalog/sprint/current`  | Current sprint board     | `application/json` | Issues in the active sprint grouped by status column.  |

Reading `jira://catalog/open-issues` might return:

```json
[
  {"key": "PLAT-812", "title": "Rotate GitHub tokens quarterly", "status": "In Progress", "assignee": "dev-a"},
  {"key": "PLAT-834", "title": "MCP server flakes on cold start",  "status": "Open",        "assignee": null}
]
```

## Why this reduces exploratory tool calls

- **Before (tools only):** the agent guesses filters, calls `search_issues`
  repeatedly, and pages through results to build a mental model of the backlog —
  many round trips, lots of tokens.
- **After (resource catalog):** the agent reads one compact catalog resource,
  sees every open issue at a glance, and calls a tool only for the *specific*
  issue it now knows it needs. Fewer calls, less context burned, faster answers.

Documentation hierarchies (`docs://catalog/tree`) and database schemas
(`db://catalog/schema`) follow the same pattern: publish the map as a resource
so the agent never has to crawl for it.
