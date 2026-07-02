# Lab 02 — Solution notes

## Approach

Two small, pure modules make the CLAUDE.md concepts testable without touching a
real filesystem or a live Claude session:

- `config_hierarchy.py` models the memory hierarchy (`resolve_config`), the
  `@import` mechanism (`resolve_imports`), and the sharing rule (`is_team_shared`).
- `tool_selection.py` maps a task description to one built-in tool (`choose_tool`).

The "filesystem" for imports is passed in as a `{path: content}` dict so results
are deterministic. The sample-project artifacts are the real-world illustration;
the tests read them to prove the code matches the docs.

## Key decisions & why

- **Precedence order = `("user", "project", "directory")`, least specific first.**
  Claude combines all layers; the more specific one wins on overlap. Emitting the
  layers in this order (directory last) makes precedence visible and matches how
  the guide describes the hierarchy (Task 3.1).
- **`is_team_shared` returns `False` only for `user`.** This encodes the exam's
  core diagnostic point: `~/.claude/CLAUDE.md` is personal and never committed, so
  team rules placed there silently fail to reach teammates.
- **Import syntax is `@path` on its own line**, resolved relative to the importing
  file via `posixpath.normpath(join(dirname(file), target))`. That is Claude
  Code's actual syntax and correctly turns `@../../standards/testing.md` inside
  `src/api/CLAUDE.md` into `standards/testing.md`.
- **Recursion with a `_seen` set** expands nested imports and guards cycles.
  Missing targets raise `FileNotFoundError` — a loud, teachable failure.
- **`choose_tool` checks rules in priority order.** The Edit→Write fallback is
  checked first (its phrases contain "unique"/"edit"), then Glob (needs a
  file/path cue so it beats Grep's generic "find"), then Grep, Write, Edit, Bash,
  Read. Overly generic keywords like bare "content" were removed so
  "read the full file contents" resolves to Read, not Grep.

## Reference walkthrough

1. `resolve_config` validates keys against `LAYER_ORDER`, iterates in order,
   skips absent layers, and joins labeled sections with blank lines.
2. `resolve_imports` splits the file into lines; a line matching `^\s*@(\S+)\s*$`
   is replaced by the recursive expansion of the resolved target; other lines
   pass through unchanged.
3. `is_team_shared` is a lookup with a `ValueError` for unknown layers.
4. `choose_tool` lowercases the input and returns on the first matching rule.

Verify:

```bash
# from labs/
LAB_TARGET=solution uv run pytest lab-02-claude-code-config-foundations -q   # green
uv run pytest lab-02-claude-code-config-foundations -q                       # red until starter is done
```

## Common mistakes

- **Ordering layers most-specific first**, or dropping the precedence signal so a
  reader can't tell which layer wins.
- **Treating user-level memory as shared** — the whole point is that it is not.
- **Resolving imports against the repo root** instead of the importing file's
  directory, which breaks relative `../` imports.
- **Forgetting the cycle guard**, causing infinite recursion on mutual imports.
- **Keyword ordering bugs in `choose_tool`**: letting generic "find" route file
  patterns to Grep instead of Glob, or letting "unique" route the Edit-failure
  fallback to Edit instead of Write.
- Returning a value not in `VALID_TOOLS`, or silently defaulting instead of
  raising on an unrecognized task.

## Checklist

- [ ] `resolve_config` orders user < project < directory and omits missing layers.
- [ ] `resolve_config` raises `ValueError` on unknown layer names.
- [ ] `is_team_shared("user")` is `False`; project/directory are `True`.
- [ ] `resolve_imports` expands nested + relative imports and removes `@` lines.
- [ ] `resolve_imports` raises `FileNotFoundError` on a missing target.
- [ ] `choose_tool` returns the right tool for all canonical Task 2.5 cases.
- [ ] `choose_tool` raises `ValueError` on an unrecognized task.
- [ ] Both `LAB_TARGET=solution` (green) and default (red on starter) confirmed.
