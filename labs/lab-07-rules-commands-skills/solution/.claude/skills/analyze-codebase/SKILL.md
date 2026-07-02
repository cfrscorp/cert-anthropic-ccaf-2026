---
name: analyze-codebase
description: >-
  Map an unfamiliar codebase — entry points, module boundaries, and key data
  flows — and return a concise summary. Use when onboarding to a new repo or
  before a large refactor. Produces verbose exploration, so it runs forked.
context: fork
allowed-tools: Read, Grep, Glob
argument-hint: "[directory or subsystem to analyze, e.g. src/api]"
---

# analyze-codebase

Analyze the codebase (or the subsystem named in `$ARGUMENTS`) and return a short
structured summary to the main session.

`context: fork` runs this skill in an isolated sub-agent context so the many
`Read`/`Grep`/`Glob` results do NOT pollute the main conversation — only the
final summary comes back. `allowed-tools` restricts it to read-only exploration
(no `Write`, `Edit`, or `Bash`), so it can never modify the tree.

## Steps

1. Use `Glob` to inventory the structure; identify entry points and config.
2. Use `Grep` to find where execution starts and how modules reference each other.
3. Use `Read` to follow the 3–5 most important files and trace key data flows.

## Output (return only this to the main session)

- **Overview**: what the code does, in 2–3 sentences.
- **Entry points**: files where execution begins.
- **Module map**: the main modules and their responsibilities.
- **Key data flows**: how a request / job moves through the system.
- **Risks / unknowns**: anything surprising or worth a closer look.
