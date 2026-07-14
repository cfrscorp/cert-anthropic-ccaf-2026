# Lab 02 — Claude Code Config Foundations

**Difficulty:** 2/10 | **Est. time:** 1:30 | **Prerequisites:** None | **Task statements:** 3.1, 2.5

## Objective

Learn how Claude Code assembles its instructions and how it picks the right tool
for a job. By the end you can:

- Explain and compute the **CLAUDE.md hierarchy** — user-level, project-level,
  and directory-level — and which layer wins when they overlap.
- Explain why **user-level memory is not shared** with teammates (and diagnose
  the "the new hire isn't getting our rules" bug).
- Expand **`@import`** references so a CLAUDE.md stays modular, and recognize the
  **`.claude/rules/`** directory as the alternative to a monolithic file.
- Recall the **`/memory`** command for seeing which memory files are loaded.
- **Select the correct built-in tool** (Read, Write, Edit, Bash, Grep, Glob) for
  canonical tasks, including the Edit → Write fallback.

## Background

Claude Code loads *memory* from a layered set of `CLAUDE.md` files:

| Layer | Location | Shared with team? |
|-------|----------|-------------------|
| user-level | `~/.claude/CLAUDE.md` | **No** — personal, not in any repo |
| project-level | repo root `CLAUDE.md` or `.claude/CLAUDE.md` | Yes — version-controlled |
| directory-level | `subdir/CLAUDE.md` | Yes — applies inside that subtree |

All applicable layers are combined; more specific layers (directory) take
precedence over more general ones (user) for overlapping instructions. A common
production bug is putting a team rule in `~/.claude/CLAUDE.md` (user-level) — it
works for its author but nobody else ever receives it, because it is never
committed. Use `/memory` in a session to see exactly which files are loaded.

To keep memory modular, a CLAUDE.md can pull in another file with an import
reference on its own line — Claude Code's syntax is `@path/to/file` (resolved
relative to the importing file). For conventions that span many directories (for
example, all test files), path-scoped files in `.claude/rules/` with a `paths:`
glob frontmatter beat directory-level CLAUDE.md files.

Separately, choosing the right built-in tool keeps work fast and reliable:

| Tool | Use it for |
|------|-----------|
| **Grep** | searching file *contents* (callers, error strings, imports) |
| **Glob** | matching file *paths* by name/extension (e.g. `**/*.test.tsx`) |
| **Read** | loading a full file's contents |
| **Write** | creating/overwriting a whole file; **fallback when Edit has no unique anchor** |
| **Edit** | a targeted change anchored on unique text |
| **Bash** | running a shell command (build, test, install, git) |

Explore the artifacts under `sample-project/` — they are a working example of the
whole hierarchy (root `CLAUDE.md`, `src/api/CLAUDE.md`, an `@import`ed
`standards/testing.md`, a path-scoped `.claude/rules/testing.md`, and a
`user-level-claude-md.example.md` note).

## Tasks

Edit only the files in `starter/`. Implement, run the tests, iterate.

1. **`config_hierarchy.is_team_shared(layer)`** — return `False` for `"user"`,
   `True` for `"project"` and `"directory"`, and raise `ValueError` otherwise.
2. **`config_hierarchy.resolve_config(layers)`** — merge the provided layers into
   one string ordered least-specific first (`user`, then `project`, then
   `directory`), skipping missing layers and labeling each section so precedence
   is visible. Reject unknown layer names with `ValueError`.
3. **`config_hierarchy.resolve_imports(path, files)`** — recursively replace each
   line that is exactly `@<path>` with the referenced file's expanded content.
   Resolve import targets relative to the importing file's directory. Raise
   `FileNotFoundError` on a missing target and guard against import cycles.
4. **`tool_selection.choose_tool(task_description)`** — return exactly one of
   `VALID_TOOLS` for the canonical Task 2.5 cases (see the table above). Order
   your checks so the Edit→Write fallback and Glob path-patterns are handled
   before generic "find"/"edit" keywords. Raise `ValueError` when nothing fits.

## Deliverables

- Completed `starter/config_hierarchy.py` and `starter/tool_selection.py` with
  all four functions implemented and the same public API as the reference.
- All tests in `tests/test_lab02.py` passing against `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-02-claude-code-config-foundations
```

You can also exercise the reference CLIs from `solution/`:

```bash
uv run solution/tool_selection.py "find all callers of process_order"   # -> Grep
uv run solution/config_hierarchy.py --demo
```

## Stretch Goals

- Add a second `@import` (e.g. `standards/security.md`) to
  `sample-project/src/api/CLAUDE.md` and confirm `resolve_imports` expands both.
- Extend `resolve_config` to detect a *conflict* (the same rule keyword in two
  layers) and report which layer wins.
- Add an `.claude/rules/` file with a `paths:` glob and write a note explaining
  when you would choose it over a directory-level CLAUDE.md (Task 3.3).
- Add a `choose_tool` case for "trace a function across wrapper modules" and
  justify why the answer is Grep (Task 2.5, incremental codebase understanding).
