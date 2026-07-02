---
name: scaffold
description: >-
  Scaffold a new module (source + matching test + registration) following the
  team's conventions. Use on demand when starting a new component, handler, or
  service. Produces exploratory reasoning about layout, so it runs forked.
context: fork
allowed-tools: Read, Write, Glob
argument-hint: "[module name and kind, e.g. users-api handler]"
---

# scaffold

Generate the boilerplate for a new module named in `$ARGUMENTS`, wiring it into
the existing project structure and honoring the path-scoped rules in
`.claude/rules/` (API handlers, tests, etc.).

`context: fork` runs this skill in an isolated sub-agent so its layout
exploration and drafting do NOT pollute the main conversation — only the final
summary of created files returns. `allowed-tools: Read, Write, Glob` restricts it
to reading the tree and writing new files (no `Bash`, no `Edit`), so it cannot
run destructive commands. `argument-hint` prompts the developer for the module
name and kind when they invoke `/scaffold` with no arguments.

## Steps

1. Use `Glob` to find a sibling of the same kind and mirror its layout.
2. Use `Read` to learn the local imports, exports, and naming conventions.
3. Use `Write` to create the source file, a matching test file, and any index /
   registration entry required.

## Output (return only this to the main session)

- **Created files**: paths of every file written.
- **Follow-ups**: anything the developer must fill in (business logic, fixtures).
