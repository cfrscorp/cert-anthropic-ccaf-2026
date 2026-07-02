---
description: TODO — one line describing what /review does.
# TODO (optional): add `argument-hint` and `allowed-tools` frontmatter.
---

# /review — team code review

TODO: write the prompt body for a shared, version-controlled code-review slash
command. Reference `$ARGUMENTS` for an optional focus path/PR, and describe the
checklist (correctness, security, conventions, tests) plus the output format.

This file lives in `.claude/commands/` so it is shared with the whole team via
git — that is exactly why a team review command belongs here and NOT in
`~/.claude/commands/` (which is personal and unshared).
