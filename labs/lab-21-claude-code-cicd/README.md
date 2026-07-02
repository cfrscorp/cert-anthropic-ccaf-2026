# Lab 21 — Claude Code in CI/CD

| | |
|---|---|
| **Task statement** | 3.6 (Integrate Claude Code into CI/CD pipelines) |
| **Difficulty** | 6 / 10 |
| **Estimated time** | 2:00 |
| **Prerequisites** | Lab 04 (structured output), Lab 07 (rules, commands & skills) |
| **Domain** | Claude Code Configuration & Workflows |

## Objective

Wire Claude Code into a pull-request review pipeline that runs **non-interactively**,
emits **schema-validated JSON**, and posts findings as **inline PR comments** —
without spamming duplicate comments on every push. You will author the CI
artifacts and implement the small library that parses Claude's output and turns
it into review comments.

By the end you can:

- Run Claude Code in CI with the `-p` / `--print` flag so the job never hangs
  waiting for interactive input (Sample Question 10).
- Use `--output-format json` + `--json-schema` to force machine-parseable findings.
- Give the CI-invoked instance project context via a checked-in `CLAUDE.md`
  (review criteria, testing standards, fixtures).
- Feed prior findings back in so re-runs report only **new / unaddressed** issues.

## Background

Running `claude "Analyze this PR"` in a CI job hangs: Claude Code defaults to
interactive mode and waits for input that never comes. The fix is the **`-p`
(`--print`) flag** — it reads the prompt, writes the result to stdout, and exits.
This is Sample Question 10: it is a real CLI flag, *not* a `CLAUDE_HEADLESS` env
var, a `--batch` flag, or a `< /dev/null` redirect (those are distractors).

For the output to be postable as inline comments it must be structured, so the
pipeline adds `--output-format json --json-schema review-schema.json`. The schema
guarantees each finding has a `location`, `issue`, `severity`, `suggested_fix`,
and a `detected_pattern` tag — no free-text parsing.

Two more ideas from Task Statement 3.6 shape the design:

- **Session context isolation.** The Claude session that *generated* code is worse
  at reviewing its own changes — it keeps its own reasoning and is less likely to
  question it. CI runs an **independent** review instance, and the checked-in
  `review.CLAUDE.md` tells it the review criteria, testing standards, and fixtures.
- **Dedupe across re-runs.** Every push re-triggers the review. If you re-post
  everything, PRs drown in duplicate comments. Feed the **prior findings** back in
  and report only issues that are new or still unaddressed.

## Tasks

Work in `starter/`. Two kinds of deliverable: the **CI artifacts** and the
**parser library** `starter/ci_review.py` (same public API as `solution/`).

1. **Fix the workflow** `starter/.github/workflows/claude-review.yml`. The
   `claude` invocation currently hangs. Add `-p` (or `--print`),
   `--output-format json`, and `--json-schema review-schema.json`.
2. **Complete the schema** `starter/review-schema.json` so each finding requires
   `location` (`path`, `line`), `issue`, `severity` (enum:
   `critical`/`high`/`medium`/`low`/`info`), `suggested_fix`, and
   `detected_pattern`. Set `additionalProperties: false`.
3. **Write `starter/review.CLAUDE.md`** — the project context for the CI-invoked
   instance: which categories to report vs skip, severity criteria, testing
   standards + fixtures, and the "independent review instance" framing.
4. **Implement `starter/ci_review.py`**:
   - `parse_findings(json_text, schema) -> list[dict]` — `json.loads` then
     validate against the schema (required keys, types, the severity enum);
     raise `ValueError` on bad JSON or a schema violation. Return the `findings`
     list. (`jsonschema` is **not** a dependency — write a small validator.)
   - `to_pr_comments(findings) -> list[dict]` — one `{"path", "line", "body"}`
     dict per finding; `body` carries severity, issue, fix, and pattern.
   - `dedupe_against_prior(new_findings, prior_findings) -> list[dict]` — keep
     only findings whose identity is not in the prior set; preserve order.
   - `workflow_uses_print_flag(workflow_yaml) -> bool` — True iff a `claude`
     command in a `run:` step carries `-p` / `--print`.

The provided `sample_claude_output.json` and `prior_findings.json` are the test
fixtures (already complete) — treat them as example Claude output.

## Deliverables

- `starter/.github/workflows/claude-review.yml` invoking
  `claude -p ... --output-format json --json-schema review-schema.json`.
- `starter/review-schema.json` with the full finding schema.
- `starter/review.CLAUDE.md` documenting review criteria / testing standards /
  fixtures.
- `starter/ci_review.py` with the four functions implemented (the wired CLI then
  works via `uv run ci_review.py --help`).

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-21-claude-code-cicd
```

All tests pass once your starter is complete. Check against the reference:

```bash
LAB_TARGET=solution uv run pytest lab-21-claude-code-cicd
```

Try the CLI too (from `solution/` or your finished `starter/`):

```bash
uv run ci_review.py --check-workflow .github/workflows/claude-review.yml
uv run ci_review.py --findings sample_claude_output.json \
    --schema review-schema.json --prior prior_findings.json --post
```

## Stretch goals

- Add a `confidence` field (0–1) to the schema and route only high-confidence
  findings to inline comments, batching the rest into a single summary comment.
- Split the review into per-file passes plus a cross-file integration pass
  (Sample Question 12 / Task 4.6) and merge the findings before dedupe.
- Make `dedupe` tolerant of small line-number drift (e.g. match on
  `path + detected_pattern + issue` within ±3 lines) so a shifted-but-identical
  finding is still recognized as already reported.
