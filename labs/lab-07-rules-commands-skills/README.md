# Lab 07 — Claude Code Rules, Commands & Skills

| | |
|---|---|
| **Difficulty** | 4 / 10 |
| **Estimated time** | 2:00 |
| **Prerequisites** | Lab 02 |
| **Task statements** | 3.2 (custom slash commands & skills), 3.3 (path-specific rules) |
| **Domain** | Claude Code Configuration & Workflows |

## Objective

Learn to configure a repository so Claude Code loads the right conventions at the
right time and exposes shared, version-controlled workflows to the whole team.
You will build three project-scoped mechanisms and the small library that parses
and validates them:

- **`.claude/rules/*.md`** — topic files with a YAML `paths:` glob that load
  *only when editing a matching file*.
- **`.claude/commands/*.md`** — project-scoped slash commands, shared via git.
- **`.claude/skills/<name>/SKILL.md`** — on-demand skills with `context: fork`,
  `allowed-tools`, and `argument-hint` frontmatter.

## Background

Claude Code has three overlapping ways to feed it project knowledge, and picking
the wrong one is a common exam trap:

| Mechanism | When it loads | Best for |
|---|---|---|
| **CLAUDE.md** | Always (every turn) | Universal standards that apply to the whole repo |
| **`.claude/rules/*.md`** with `paths:` globs | Only when editing a matching file | Conventions tied to a file *type* or area, especially when those files are scattered across directories |
| **Skills** (`.claude/skills/<name>/SKILL.md`) | On demand, when invoked | Task-specific workflows (analysis, scaffolding) you trigger deliberately |

Two rules of thumb the exam leans on:

- **Scattered files → path-scoped rules, not subdirectory CLAUDE.md.** Test files
  live next to the code they test (`Button.test.tsx` beside `Button.tsx`) all over
  the tree. A glob like `**/*.test.tsx` in `.claude/rules/testing.md` applies the
  same conventions everywhere; a per-directory `CLAUDE.md` cannot follow files
  spread across dozens of folders. (Sample Question 6.)
- **Team-shared workflow → `.claude/commands/`, not `~/.claude/commands/`.** Files
  under `.claude/` are version-controlled and reach every developer on clone/pull.
  `~/.claude/commands/` is personal and unshared. (Sample Question 4.)

Skills add two more knobs. `context: fork` runs the skill in an isolated
sub-agent so its verbose output (e.g. a full codebase crawl) never pollutes the
main conversation; only the summary returns. `allowed-tools` restricts what the
skill may do (e.g. read-only `Read, Grep, Glob`), and `argument-hint` prompts the
developer for parameters when they invoke the skill bare.

## Tasks

Work in `starter/`. Two kinds of deliverable: the **config artifacts** under
`starter/.claude/`, and the **parser library** `starter/claude_config.py`.

1. **Complete the rule files** in `starter/.claude/rules/`:
   - `testing.md` → `paths: ["**/*.test.tsx", "**/*.test.ts"]`
   - `api.md` → `paths: ["src/api/**/*"]`
   - `terraform.md` → `paths: ["terraform/**/*"]`
   Each also gets a short body documenting the conventions.
2. **Complete `starter/.claude/commands/review.md`** — a team code-review slash
   command with a `description` (and, ideally, `argument-hint` / `allowed-tools`).
3. **Complete `starter/.claude/skills/analyze-codebase/SKILL.md`** — fix the
   frontmatter so it declares `context: fork`, `allowed-tools`, and
   `argument-hint`, and remove any keys that are not valid.
4. **Implement `starter/claude_config.py`** (same public API as `solution/`):
   - `parse_frontmatter(markdown_text) -> dict` — extract the leading YAML block.
   - `rules_for_path(path, rules) -> list[str]` — names of rules whose `paths`
     globs match `path`. Your matcher **must** handle `**` across directories
     (`**/*.test.tsx` matches both `Button.test.tsx` and `src/ui/Button.test.tsx`).
   - `validate_skill_frontmatter(fm) -> list[str]` — return a list of problems
     (empty means valid): require `description`, allow only the known keys, require
     `context == "fork"` when present, and require non-empty `allowed-tools` /
     `argument-hint` when present.

## Deliverables

- `starter/.claude/rules/{testing,api,terraform}.md` with correct `paths:` globs.
- `starter/.claude/commands/review.md`.
- `starter/.claude/skills/analyze-codebase/SKILL.md` with valid frontmatter.
- `starter/claude_config.py` with the three functions implemented.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-07-rules-commands-skills
```

All tests should pass once your starter is complete. To check your work against
the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-07-rules-commands-skills
```

## Stretch Goals

- Add a `.claude/rules/database.md` scoped to a repository-pattern layer (e.g.
  `paths: ["src/models/**/*"]`) and a test asserting a model file routes to it.
- Add a **personal** variant of the skill under `~/.claude/skills/` with a
  different name, and explain in a comment why renaming avoids clobbering the
  team skill for teammates.
- Extend `validate_skill_frontmatter` to accept `allowed-tools` scoped to
  patterns like `Bash(git diff:*)` and add a test for it.
