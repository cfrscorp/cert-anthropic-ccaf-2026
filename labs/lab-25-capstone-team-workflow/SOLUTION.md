# Lab 25 — Solution

## Approach

This capstone has two mutually-reinforcing halves:

1. **Author a complete, version-controlled `.claude/` configuration** for a team
   the way a real repo would — project memory with an `@import`, path-scoped
   rules, a shared command, a forked skill, MCP config with env expansion, and a
   CI workflow that consumes all of it.
2. **Implement one auditor library** (`validate_config.py`) that reads those
   artifacts and returns a list of problems (empty == well-formed), plus the
   three pure helpers the capstone re-implements from the prerequisite labs
   (`rules_for_path`, `expand_env`, `choose_mode`).

The reference config lives in `solution/`; tests read whichever target
`LAB_TARGET` selects via `labkit.target_dir`, so the same test file validates the
solution and fails against the starter stubs. A deliberately broken tree under
`fixtures/broken/` proves `validate_project` reports problems, not just accepts.

## Key decisions & why

Each artifact maps to a specific exam answer:

- **Team command in `.claude/commands/review.md` (Sample Q4 → A).** Project-scoped
  commands live in the repo's `.claude/commands/`, so they are version-controlled
  and reach every developer on clone/pull. `~/.claude/commands/` (Q4 distractor B)
  is personal and unshared; CLAUDE.md (C) holds context, not command definitions;
  a `config.json` commands array (D) does not exist. `validate_project` enforces
  the file's presence *and* a frontmatter `description`.
- **Plan mode for the microservice restructuring (Sample Q5 → A).** `choose_mode`
  returns `"plan"` when the task is architectural, multi-approach, multi-file, or
  unclear in scope — the monolith→microservices case is all four, so its
  complexity is *stated up front* and you plan before touching code. A single-file
  fix with a clear stack trace has none of these triggers → `"direct"`.
- **Path-scoped rules with globs (Sample Q6 → A).** Test files sit next to the
  code they cover throughout the tree, so `testing.md` uses
  `paths: ["**/*.test.tsx", "**/*.test.ts"]`. A glob follows the file *type*
  regardless of directory; a per-directory CLAUDE.md (Q6 distractor D) cannot, and
  a monolithic CLAUDE.md relying on inference (B) is unreliable. `api.md`
  (`src/api/**/*`) and `terraform.md` (`terraform/**/*`) scope by area.
  `validate_project` requires every rule to declare a non-empty `paths` list.
- **CI runs `claude -p` with a schema (Sample Q10 → A / Task 3.6).** The workflow
  invokes `claude -p ... --output-format json --json-schema review-schema.json`.
  `-p`/`--print` runs non-interactively so the job never hangs waiting for input
  (Q10 distractors — `CLAUDE_HEADLESS`, `--batch`, stdin redirection — are
  non-existent or workarounds). `--output-format json` + `--json-schema` force
  schema-valid, machine-parseable findings CI can post as inline comments. A
  *fresh* CI instance reviews the diff (more effective than self-review).
- **CLAUDE.md hierarchy + `@import` (Task 3.1).** Universal standards go in the
  project-level `.claude/CLAUDE.md` (shared via git); the testing standards are
  factored into `standards/testing.md` and pulled in with `@standards/testing.md`
  to keep memory modular. `validate_project` checks that every `@import` resolves.
- **Skill frontmatter (Task 3.2).** `scaffold` sets `context: fork` so its verbose
  layout exploration runs isolated and only a summary returns; `allowed-tools:
  Read, Write, Glob` keeps it from running `Bash`/`Edit`; `argument-hint` prompts
  for the module name. Unknown keys and a `context` other than `fork` are flagged.
- **MCP scope + secrets (Task 2.4).** Shared servers live in `.mcp.json` with
  `${GITHUB_TOKEN}` expansion (never a committed token); personal/experimental
  servers live in the user-scope `user-claude.json`. Tools from both scopes are
  available simultaneously. `has_hardcoded_secret` rejects a baked-in credential.

## Reference walkthrough

- `validate_project(root)` runs seven checks against `root`: CLAUDE.md present;
  every `@import` resolves relative to CLAUDE.md's directory; every rule has a
  non-empty `paths` list; `commands/review.md` present with a `description`; every
  `skills/*/SKILL.md` passes `validate_skill_frontmatter`; `.mcp.json` has no
  hardcoded secret; and `claude-ci.yml` contains `-p`/`--print` and
  `--json-schema`. It returns the accumulated problem strings.
- `rules_for_path` translates each glob to a regex where `**/` → `(?:.*/)?`,
  `**` → `.*`, `*` → `[^/]*`, `?` → `[^/]`, so `**/*.test.tsx` matches both
  top-level and nested test files and `src/api/**/*` matches `src/api/users.ts`
  and `src/api/v1/handlers.ts`.
- `expand_env` walks the config recursively, substituting each `${VAR}` from the
  env mapping and raising `KeyError(name)` on a missing variable.
- `has_hardcoded_secret` treats a pure `${VAR}` placeholder as safe, but flags a
  known credential shape (`ghp_...`, `sk-ant-...`, ...) or a non-empty literal
  under a credential-named key.
- `choose_mode` returns `"plan"` on any plan trigger (architectural /
  multiple-approaches / multi-file / unclear scope), else `"direct"`.
- The module also ships a CLI (`validate_config.py <root>`) with PEP 723
  metadata, `-h` with an Examples epilog, `__version__`, and `--version`, exiting
  0 when clean and 1 with a problem list otherwise.

## Common mistakes

- **Putting `/review` in `~/.claude/commands/`.** It then won't be shared via git;
  the exam's correct home is the project `.claude/commands/`.
- **Using a per-directory CLAUDE.md for test conventions.** Test files are
  scattered, so a `**/*.test.tsx` glob rule is the maintainable choice.
- **`fnmatch`/`PurePath.match` for globs.** They treat `*` as matching `/`, so
  `**/*.test.tsx` fails to match a top-level `Widget.test.ts`. Handle the
  zero-segment `**/` case explicitly.
- **Committing a real token in `.mcp.json`.** Use `${VAR}` expansion; a literal
  `ghp_...` (or any value under a `*_TOKEN` key) is a hardcoded secret.
- **Running `claude` without `-p` in CI.** The job hangs on interactive input.
  Also add `--json-schema` for machine-parseable output.
- **Setting `context: forked`** (or any value but `fork`) or leaving
  `allowed-tools`/`argument-hint` empty in SKILL.md — all flagged.
- **`@import` pointing at a missing file.** Resolve it relative to the CLAUDE.md
  file's own directory and make sure the target exists.

## Checklist

- [ ] `.claude/CLAUDE.md` present with universal standards and `@standards/testing.md`.
- [ ] `.claude/standards/testing.md` exists so the import resolves.
- [ ] `.claude/rules/{api,testing,terraform}.md` each declare correct `paths:` globs.
- [ ] `.claude/commands/review.md` present with a frontmatter `description`.
- [ ] `.claude/skills/scaffold/SKILL.md` has `context: fork`, `allowed-tools`,
      `argument-hint`, a `description`, and no unknown keys.
- [ ] `.mcp.json` uses `${VAR}` expansion (no hardcoded secret);
      `user-claude.json` shows a user-scope server.
- [ ] `.github/workflows/claude-ci.yml` runs `claude -p ... --output-format json
      --json-schema review-schema.json`; `review-schema.json` defines the findings.
- [ ] `validate_config.py` implements `validate_project`, `rules_for_path`,
      `expand_env`, `has_hardcoded_secret`, `choose_mode` (+ `parse_frontmatter`,
      `load_rules`).
- [ ] `LAB_TARGET=solution uv run pytest lab-25-capstone-team-workflow` is green;
      the default (starter) run fails until the work is complete.
