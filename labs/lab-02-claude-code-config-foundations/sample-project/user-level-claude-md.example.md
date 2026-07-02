# Example of a USER-LEVEL CLAUDE.md

> This file is only an illustration. A real user-level memory file lives at
> `~/.claude/CLAUDE.md` on **your own machine** — NOT inside the repo. It is
> intentionally shown here (with a `.example.md` name) so it is never mistaken
> for the project's committed memory.

## Why this matters (Task Statement 3.1)

Instructions in `~/.claude/CLAUDE.md` apply to **every project you personally
work on**, but they are **not shared with teammates** because they are not part
of any repository. This is the classic hierarchy bug:

> "A new team member isn't getting our commit-message rules."
> Cause: the rules were placed in one maintainer's `~/.claude/CLAUDE.md`
> (user-level) instead of the project's committed `CLAUDE.md` (project-level),
> so nobody else ever received them.

Fix: move anything the whole team must follow into the project-level
`CLAUDE.md` (or `.claude/rules/`), which is version-controlled.

## Example personal preferences (fine to keep user-level)

- Explain your reasoning before large refactors.
- Prefer concise commit summaries in my personal style.
- Use `uv run` to execute Python scripts.

Verify what is actually loaded in any session with the `/memory` command.
