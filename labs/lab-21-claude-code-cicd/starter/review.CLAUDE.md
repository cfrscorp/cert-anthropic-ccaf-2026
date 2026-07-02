# CI Review Standards (project context for CI-invoked Claude Code)

<!--
TODO: Fill this in. This file is committed and auto-loaded when Claude Code runs
in the review job — it is how you give the CI-invoked instance project context
(Task Statement 3.6). Cover, at minimum:

- That this is an INDEPENDENT review instance (it did not generate the code).
- WHICH finding categories to report (security, correctness bugs, missing tests)
  and which to SKIP (style, local conventions) — explicit criteria reduce false
  positives and protect developer trust.
- Explicit severity criteria (critical/high/medium/low/info).
- Testing standards + available fixtures so generated tests avoid duplicates.
- The output contract: findings must match review-schema.json, and re-runs
  should report only NEW / still-unaddressed issues (see prior_findings.json).

See solution/review.CLAUDE.md for a reference.
-->
