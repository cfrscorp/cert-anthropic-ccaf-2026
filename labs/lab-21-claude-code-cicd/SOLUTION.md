# L21 — Solution Notes

## Approach

The lab splits into a **CI-configuration** half (the workflow, the JSON schema,
and the checked-in `review.CLAUDE.md`) and a **deterministic library** half
(`ci_review.py`) that consumes Claude's structured output offline. No live Claude
is needed: the `--json-schema`-enforced JSON *is* Claude's contribution, and the
tests feed a canned `sample_claude_output.json` through the same code the CI job
runs. That mirrors the real pipeline — Claude produces JSON, plumbing turns it
into PR comments.

## Key decisions & why

### `-p` / `--print` is the fix — tie to Sample Question 10

A CI job that runs `claude "Analyze this PR"` hangs because Claude Code defaults
to interactive mode. The correct, documented fix is the **`-p` / `--print`
flag**: it processes the prompt, writes to stdout, and exits. The three
distractors in Sample Q10 all fail:

- `CLAUDE_HEADLESS=true` — no such environment variable.
- `--batch` — no such flag (and the Message Batches API is a different thing,
  unsuitable for blocking pre-merge checks — see Sample Q11).
- `claude "..." < /dev/null` — a Unix hack that does not address Claude Code's
  actual command syntax.

`workflow_uses_print_flag` encodes exactly this: it accepts only `-p` / `--print`
as a token on a `claude` command line, and the
`test_workflow_distractors_do_not_count_as_print_flag` case proves the env var /
`--batch` / stdin-redirect forms return `False`.

### Independent review instance beats self-review

Task Statement 3.6 (and 4.6) stress **session context isolation**: the session
that generated the code retains its reasoning and is less likely to question its
own decisions, so it makes a poor reviewer of its own diff. The CI job therefore
runs a fresh, independent instance, and `review.CLAUDE.md` supplies the context
that instance lacks — review criteria, severity definitions, testing standards,
and available fixtures. This is why the context lives in a **checked-in
`CLAUDE.md`**, not in the ephemeral prompt: it reaches every CI run and every
teammate via version control.

### Schema-enforced structured output

`--output-format json --json-schema review-schema.json` guarantees each finding
is schema-shaped, so `to_pr_comments` never parses free text. `parse_findings`
still validates defensively (CI must fail loudly, not post garbage). Because
`jsonschema` is not a lab dependency, the solution ships a ~40-line draft-07
subset validator covering `type`, `enum`, `required`, `properties`,
`additionalProperties`, `items`, `minimum`, `minLength` — enough for this schema
and fully deterministic. Note bools are rejected for numeric types so a JSON
`true` cannot satisfy `line: integer`.

### Dedupe to avoid duplicate comments

Every push re-runs the review. Feeding `prior_findings.json` back in and reporting
only new/unaddressed issues is the difference between a useful bot and one that
buries a PR in repeats. The identity key is `(path, line, detected_pattern,
issue)` — stable enough that the same issue at the same place is recognized as
already-reported. `detected_pattern` exists precisely to give findings a stable
machine tag (it also enables false-positive analysis per Task 4.4).

## Reference walkthrough

1. **`parse_findings`** — `json.loads` (ValueError on syntax error) → `_validate`
   against the schema (ValueError with the collected errors) → return
   `data["findings"]`.
2. **`_validate`** — recursive; checks `type` first (short-circuits so later
   checks assume the type held), then `enum` / `required` / `additionalProperties`
   / `items` / numeric & string bounds.
3. **`to_pr_comments`** — one `{"path", "line", "body"}` per finding; `body`
   embeds severity, issue, suggested fix, and pattern so the diff comment is
   self-contained.
4. **`dedupe_against_prior`** — build the set of prior `_finding_key`s, keep new
   findings whose key is absent, preserve input order.
5. **`workflow_uses_print_flag`** — `yaml.safe_load`, walk `jobs → steps → run`,
   join backslash-newline continuations, `shlex.split` each line, and accept only
   a line where `claude` and (`-p` or `--print`) are both tokens. Falls back to
   scanning raw text if the YAML has no structured runs.
6. **CLI** — `--check-workflow` validates a workflow (exit 1 if it would hang);
   `--findings/--schema/--prior/--post` runs parse → dedupe → emit comments.

## Common mistakes

- **Reaching for a distractor instead of `-p`.** `CLAUDE_HEADLESS`, `--batch`,
  and `< /dev/null` all leave the job hanging or misbehaving. Only `-p`/`--print`.
- **Accepting `-p` anywhere in the file.** The flag must be on a `claude`
  command. A loose substring search would wrongly pass a workflow that mentions
  `-p` in a comment or on an unrelated command. Tokenize the command line.
- **Putting review criteria in the prompt instead of `CLAUDE.md`.** Prompt-only
  context is not shared or versioned; the checked-in `CLAUDE.md` is how every CI
  run and teammate gets the same standards (and how you cut false positives).
- **Skipping dedupe.** Without it, each push re-posts every finding — the fastest
  way to get a review bot muted.
- **Weak schema validation.** Returning findings without checking the severity
  enum or the `line` type lets malformed output become malformed PR comments.
- **Self-review.** Reviewing in the same session that generated the code misses
  subtle issues; use an independent instance.

## Checklist

- [ ] Workflow runs `claude -p ... --output-format json --json-schema review-schema.json`.
- [ ] `review-schema.json` requires all five finding fields + the severity enum,
      with `additionalProperties: false`.
- [ ] `review.CLAUDE.md` documents report/skip categories, severity criteria,
      testing standards + fixtures, and the independent-instance framing.
- [ ] `parse_findings` validates the sample and rejects invalid JSON / bad enum /
      wrong types.
- [ ] `to_pr_comments` maps `path`/`line` and puts issue+fix+pattern in `body`.
- [ ] `dedupe_against_prior` drops the already-reported SQL-injection finding and
      keeps the two new ones, preserving order.
- [ ] `workflow_uses_print_flag` is True for the target workflow, False for the
      bare/`--batch`/`CLAUDE_HEADLESS`/redirect variants.
- [ ] `LAB_TARGET=solution uv run pytest lab-21-claude-code-cicd` is green;
      `uv run pytest lab-21-claude-code-cicd` fails against the starter.
