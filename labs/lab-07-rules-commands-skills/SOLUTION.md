# Lab 07 — Solution

## Approach

The lab has two halves that reinforce each other:

1. **Author the config artifacts** under `.claude/` the way a real repo would:
   three path-scoped rule files, one shared slash command, and one skill.
2. **Implement the tiny parser library** (`claude_config.py`) that reads and
   validates those artifacts, so the concepts are exercised mechanically (and the
   tests can be deterministic and offline).

The reference config lives in `solution/.claude/`; the tests read whichever
target `LAB_TARGET` selects via `labkit.target_dir`, so the same test file
validates the solution and fails against the starter stubs.

## Key decisions & why

- **Path-scoped rules for scattered files (Task 3.3 / Sample Q6).** Test files
  sit next to the code they cover throughout the tree, so `testing.md` uses
  `paths: ["**/*.test.tsx", "**/*.test.ts"]`. A glob rule follows the file *type*
  regardless of directory; a per-directory `CLAUDE.md` (distractor D in Q6) is
  directory-bound and cannot. `api.md` (`src/api/**/*`) and `terraform.md`
  (`terraform/**/*`) show the complementary case — conventions scoped to one
  *area* — but still expressed as globs so they load only when relevant, saving
  context/tokens versus an always-loaded CLAUDE.md (distractor B).
- **Team command in `.claude/commands/` (Task 3.2 / Sample Q4).** `review.md`
  lives in the project's `.claude/commands/` so it is version-controlled and
  reaches every developer on clone/pull. `~/.claude/commands/` (Q4 distractor B)
  is personal and unshared; a `commands` array in `config.json` (D) does not
  exist; CLAUDE.md (C) holds context, not command definitions.
- **Skill frontmatter (Task 3.2).** `analyze-codebase` sets `context: fork` so
  its verbose crawl runs in an isolated sub-agent and only the summary returns to
  the main session; `allowed-tools: Read, Grep, Glob` keeps it read-only; and
  `argument-hint` prompts for the directory to analyze. Codebase analysis is the
  canonical "verbose, on-demand" workload the guide names for `context: fork`.
- **`**`-aware glob matching.** Plain `fnmatch` is wrong here: it treats `*` as
  matching `/` too, so it cannot express "single segment vs. any depth." The
  solution translates the glob to a regex where `**/` → `(?:.*/)?` (zero-or-more
  segments), `**` → `.*`, `*` → `[^/]*`, and `?` → `[^/]`. That makes
  `**/*.test.tsx` match top-level *and* nested test files, and `src/api/**/*`
  match `src/api/users.ts` *and* `src/api/v1/handlers.ts`.

## Reference walkthrough

- `parse_frontmatter` tolerates a BOM/leading blank lines, requires an opening
  `---` fence, finds the closing `---`, and `yaml.safe_load`s the block. Anything
  malformed or non-mapping returns `{}`.
- `rules_for_path` matches a path against every glob in each rule's `paths` list
  (OR within a rule) and returns the matching rules' names. Names come from the
  filename stem in the tests (`testing.md` → `"testing"`).
- `validate_skill_frontmatter` returns a list of problems (empty == valid):
  missing `description`, unknown keys, `context != "fork"`, empty/malformed
  `allowed-tools`, and empty `argument-hint`.

## Common mistakes

- Using `fnmatch`/`PurePath.match` and finding `**/*.test.tsx` fails to match a
  top-level `Widget.test.ts`, or `src/api/**/*` fails to match `src/api/users.ts`
  (no nested dir). Handle the zero-segment case for `**/`.
- Putting the shared command in `~/.claude/commands/` — teammates never get it.
- Reaching for a subdirectory `CLAUDE.md` for test conventions — it cannot cover
  files scattered across the tree (Sample Q6).
- Using a skill (manual/opportunistic invocation) when the requirement is
  *automatic* application by file path — that is what rules are for.
- Writing `context: forked` or `tools:` in SKILL.md frontmatter — the valid keys
  are `context: fork` and `allowed-tools`.
- Making skill outputs pollute the main session by omitting `context: fork`.

## Checklist

- [ ] `testing.md` → `paths: ["**/*.test.tsx", "**/*.test.ts"]`
- [ ] `api.md` → `paths: ["src/api/**/*"]`; `terraform.md` → `paths: ["terraform/**/*"]`
- [ ] `review.md` in `.claude/commands/` with a `description`
- [ ] `SKILL.md` frontmatter: `context: fork`, `allowed-tools`, `argument-hint`, valid keys only
- [ ] `parse_frontmatter`, `rules_for_path` (`**`-aware), `validate_skill_frontmatter` implemented
- [ ] `uv run pytest lab-07-rules-commands-skills` passes from `labs/`
- [ ] `LAB_TARGET=solution uv run pytest lab-07-rules-commands-skills` passes
