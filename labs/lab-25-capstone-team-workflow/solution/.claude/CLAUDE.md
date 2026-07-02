# Team Project — Project Memory (project-level)

This file lives at `.claude/CLAUDE.md` and is committed to version control, so
**every teammate who clones or pulls the repo gets these instructions
automatically.** This is the project-level layer of the CLAUDE.md hierarchy —
the right home for *universal* standards that apply everywhere, always loaded on
every turn. Anything that should apply only to certain file types belongs in a
path-scoped `.claude/rules/*.md` file instead; anything personal belongs in
your own `~/.claude/CLAUDE.md`, which is **not** shared with teammates.

## Universal coding standards

- Use type hints (or the language equivalent) on all public functions.
- Prefer pure functions; push I/O to the edges of the system.
- Keep functions small and single-purpose; name things for behavior.
- Never commit secrets. Reference credentials through environment variables.

## Testing

The testing standards are kept in a separate, focused file and pulled in with an
`@import` so they can be reused by other memory files without copy/paste. Keeping
the import modular is the pattern the exam calls out for large CLAUDE.md files:

@standards/testing.md

## How our Claude Code config is organized

- **Path-scoped rules** in `.claude/rules/` load only when editing matching
  files (see `api.md`, `testing.md`, `terraform.md`).
- **Team commands** live in `.claude/commands/` (e.g. `/review`).
- **Skills** live in `.claude/skills/` (e.g. `scaffold`) and run on demand.
- **MCP servers** are configured in `.mcp.json` with `${VAR}` expansion.
