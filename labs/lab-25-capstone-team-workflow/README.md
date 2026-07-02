# Lab 25 — Capstone: Claude Code Team & CI Workflow

| | |
|---|---|
| **Scenarios** | S2 (Code Generation with Claude Code) · S4 (Developer Productivity) · S5 (Claude Code for CI) · Preparation Exercise 2 |
| **Difficulty** | 8 / 10 |
| **Estimated time** | 3:00 |
| **Prerequisites** | Lab 07, Lab 08, Lab 15, Lab 21 |
| **Task statements** | 2.4 (MCP integration), 3.1 (CLAUDE.md hierarchy & `@import`), 3.2 (commands & skills), 3.3 (path-scoped rules), 3.4 (plan vs direct), 3.6 (CI/CD integration) |
| **Domains** | Claude Code Configuration & Workflows · Tool Design & MCP Integration |

## Objective

Bring the whole Claude Code configuration story together for a real team. In one
project you will build a complete, version-controlled `.claude/` configuration
**and** the CI wiring that consumes it, then write the small "auditor" library
that proves the configuration is well-formed. This capstone integrates the pieces
you practised separately in L07 (rules/commands/skills), L08 (plan vs direct),
L15 (MCP integration), and L21 (CI review) into a single coherent workflow.

By the end you will have produced:

- a project-level **`.claude/CLAUDE.md`** of universal standards that pulls in a
  standards file via **`@import`**;
- path-scoped **`.claude/rules/{api,testing,terraform}.md`** with `paths:` globs;
- a project-scoped **`.claude/commands/review.md`** slash command;
- a **`.claude/skills/scaffold/SKILL.md`** with `context: fork`, `allowed-tools`,
  and `argument-hint`;
- a project **`.mcp.json`** using `${VAR}` expansion (no committed secret) plus a
  user-scope example (`user-claude.json`);
- a CI workflow (**`.github/workflows/claude-ci.yml`**) that runs
  `claude -p ... --output-format json --json-schema review-schema.json`;
- and `validate_config.py`, which audits all of the above and encodes the
  plan-vs-direct decision.

## Background

Each Claude Code configuration mechanism has a *correct home* the exam tests
directly. The trap answers all involve putting a thing in the wrong place or
loading it at the wrong time.

| Concern | Right home | Why (exam) |
|---|---|---|
| Universal standards, always loaded | `.claude/CLAUDE.md` (+ `@import` for modules) | Task 3.1 |
| Conventions for a file *type* scattered across the tree | `.claude/rules/*.md` with `paths:` globs | Sample Q6 |
| Team-shared slash command | `.claude/commands/` (version-controlled) | Sample Q4 |
| On-demand, verbose workflow | `.claude/skills/<name>/SKILL.md` with `context: fork` | Task 3.2 |
| Shared MCP servers + secrets | `.mcp.json` with `${VAR}` expansion | Task 2.4 |
| Personal/experimental MCP servers | user scope (`~/.claude.json`) | Task 2.4 |
| Complex, architectural, multi-file work | plan mode | Sample Q5 |
| Running Claude in CI without hanging | `-p`/`--print` + `--json-schema` | Sample Q10 / Task 3.6 |

Two integration ideas tie it together:

- **Loaded-always vs loaded-on-match vs loaded-on-demand.** CLAUDE.md is always
  in context; rules load only when you edit a matching path (saving tokens);
  skills load only when invoked. Choosing the right one is the core skill.
- **CI reuses the committed config.** Because `.claude/CLAUDE.md` and
  `.claude/rules/` are version-controlled, the CI-invoked `claude -p` inherits
  the same standards a developer has locally — no prompt duplication. A *fresh*
  CI instance reviewing the diff is also more effective than a self-review by the
  instance that wrote the code (Task 3.6).

## Tasks

Work in `starter/`. There are two halves: the **config artifacts** under
`starter/.claude/` (and `starter/.github/`, `starter/.mcp.json`, etc.), and the
**auditor library** `starter/validate_config.py`. The tests read the config from
whichever target `LAB_TARGET` selects, so completing the artifacts *and* the
library is what turns the suite green.

1. **Project memory + `@import` (Task 3.1).** In `starter/.claude/CLAUDE.md`,
   write universal standards and add `@standards/testing.md` so the shared
   testing standards are imported. (`starter/.claude/standards/testing.md`
   already exists for the import to resolve to.)
2. **Path-scoped rules (Task 3.3 / Sample Q6).** Give each rule file a `paths:`
   glob:
   - `testing.md` → `["**/*.test.tsx", "**/*.test.ts"]` (test files live all over
     the tree, so a glob beats a per-directory CLAUDE.md);
   - `api.md` → `["src/api/**/*"]`;
   - `terraform.md` → `["terraform/**/*"]`.
3. **Team command (Task 3.2 / Sample Q4).** Complete
   `starter/.claude/commands/review.md` with a `description` (and ideally
   `argument-hint` / `allowed-tools`). It stays under `.claude/commands/` so every
   teammate gets it on clone/pull.
4. **Skill (Task 3.2).** Fix `starter/.claude/skills/scaffold/SKILL.md`
   frontmatter: non-empty `description`, `context: fork`, non-empty
   `allowed-tools`, non-empty `argument-hint`, and remove any invalid keys.
5. **MCP config (Task 2.4).** In `starter/.mcp.json`, configure a shared server
   with `${VAR}` expansion for its token (no hardcoded secret). Add a personal
   server to `starter/user-claude.json` to show user vs project scope.
6. **CI workflow (Task 3.6 / Sample Q10).** Fix the `claude` invocation in
   `starter/.github/workflows/claude-ci.yml` so it uses `-p` (or `--print`),
   `--output-format json`, and `--json-schema review-schema.json`. Fill in
   `starter/review-schema.json` with the findings schema.
7. **Auditor library.** Implement `starter/validate_config.py` (same public API
   as `solution/`):
   - `validate_project(root) -> list[str]` — run all seven checks above; return
     `[]` for a well-formed config, problem strings otherwise.
   - `rules_for_path(path, rules) -> list[str]` — `**`-aware glob routing (L07).
   - `expand_env(config, env) -> dict` — resolve `${VAR}`; raise `KeyError` on a
     missing variable (L15).
   - `has_hardcoded_secret(config) -> bool` — detect a baked-in credential.
   - `choose_mode(task) -> "plan" | "direct"` — plan-vs-direct logic (L08).
   - keep `parse_frontmatter` and `load_rules` public (the tests use them).

## Deliverables

- `starter/.claude/CLAUDE.md` (+ working `@standards/testing.md` import).
- `starter/.claude/rules/{api,testing,terraform}.md` with correct `paths:` globs.
- `starter/.claude/commands/review.md` with a `description`.
- `starter/.claude/skills/scaffold/SKILL.md` with valid frontmatter.
- `starter/.mcp.json` (no hardcoded secret) and `starter/user-claude.json`.
- `starter/.github/workflows/claude-ci.yml` (`-p` + `--output-format json` +
  `--json-schema`) and `starter/review-schema.json`.
- `starter/validate_config.py` with the public API implemented.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-25-capstone-team-workflow
```

All tests should pass once your starter is complete. To check against the
reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-25-capstone-team-workflow
```

You can also run the auditor as a CLI (it follows the project script
conventions — `-h`, `--version`):

```bash
uv run lab-25-capstone-team-workflow/solution/validate_config.py solution
uv run lab-25-capstone-team-workflow/solution/validate_config.py --help
```

## Stretch goals

- Add a `.claude/rules/react.md` scoped to `["**/*.tsx"]` for component
  conventions, and extend `validate_project` to require at least N rule files.
- Add a re-review step to the CI workflow that passes *prior* findings back to
  `claude -p` and instructs it to report only new or still-unaddressed issues
  (Task 3.6), so repeated runs don't duplicate PR comments.
- Split the CI review into per-file passes plus a cross-file integration pass
  (Sample Q12) and reflect that structure in `review-schema.json`.
- Add a personal skill variant under `~/.claude/skills/` with a different name
  and explain why renaming avoids clobbering the shared team skill.
