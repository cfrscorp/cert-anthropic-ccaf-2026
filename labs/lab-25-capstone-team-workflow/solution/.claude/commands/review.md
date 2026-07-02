---
description: Run the team's standard code-review checklist on the current diff.
argument-hint: "[optional: path or PR number to focus on]"
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*)
---

# /review — team code review

Review the current changes against our shared checklist. Focus area (optional):
$ARGUMENTS

Because this command lives in `.claude/commands/` it is version-controlled and
available to every developer who clones or pulls the repo — no per-machine setup
(Sample Question 4). `~/.claude/commands/` would be personal and unshared.

## Steps

1. Get the diff under review: `git diff --merge-base origin/main` (or the path /
   PR passed in `$ARGUMENTS`).
2. Review each changed file for:
   - **Correctness**: logic bugs, off-by-one, unhandled `null`/`undefined`,
     incorrect error handling.
   - **Security**: injection, missing input validation, leaked secrets, unsafe
     deserialization.
   - **Conventions**: the path-scoped rules in `.claude/rules/` for the file type
     (tests, API handlers, Terraform).
   - **Tests**: are new behaviors covered? Do existing tests still make sense?
3. Do a cross-file integration pass: check data flow and contracts between the
   changed files, not just each file in isolation.

## Output

For each finding report: `file:line — severity (blocker/warning/nit) — issue —
suggested fix`. Skip pure style nits already enforced by the formatter. Report
only issues where the claimed problem genuinely contradicts the code — do not
invent findings to fill space. If the diff is clean, say so explicitly.
