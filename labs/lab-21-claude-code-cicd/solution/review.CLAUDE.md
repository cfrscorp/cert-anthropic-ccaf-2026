# CI Review Standards (project context for CI-invoked Claude Code)

This file is committed to the repo and loaded automatically when Claude Code runs
in the review job. It gives the **CI-invoked instance** the project context it
needs — review criteria, testing standards, and available fixtures — so findings
are actionable and low-noise (Task Statement 3.6).

## This is an independent review instance

The Claude session that runs here did **not** generate the code under review. A
generator session retains its own reasoning context and is worse at questioning
its own decisions, so an independent instance catches more subtle issues. Review
the diff on its own merits; do not assume the author's intent was correct.

## Report only these categories

Precision matters more than recall: a category with a high false-positive rate
erodes trust in every category. Report a finding **only** when it fits one of
these, with a concrete severity:

- **Security** (`critical`/`high`): injection (SQL/command/template), missing
  authz checks, secrets in code, unsafe deserialization, path traversal.
- **Correctness bugs** (`high`/`medium`): logic that contradicts the surrounding
  code's intent, off-by-one, unhandled `None`/empty, swallowed exceptions,
  resource leaks.
- **Missing tests** (`medium`/`low`): a new branch or endpoint with no covering
  test. See fixtures below before suggesting a scenario.

## Do NOT report

- Pure style/formatting (handled by the linter/formatter).
- Local conventions already used consistently elsewhere in the file.
- Speculative "could be faster" comments without a measured impact.
- Anything you cannot tie to a specific `path` + `line`.

## Severity criteria

| Severity | Use when |
|---|---|
| `critical` | Exploitable security hole or data-loss bug reachable in production. |
| `high` | Definite bug or security weakness; would fail in a realistic case. |
| `medium` | Real defect with limited blast radius, or a missing test for new logic. |
| `low` | Minor correctness/maintainability issue worth a nudge. |
| `info` | Context-only note; no action required. |

## Testing standards & available fixtures

Provide existing test files in context so generated tests avoid duplicating
scenarios already covered. Conventions:

- Tests live in `tests/`, named `test_<module>.py`, using `pytest`.
- Prefer table-driven cases; one behavior per test function.
- Available fixtures (do not re-implement): `db_session`, `authed_client`,
  `sample_order`, `frozen_clock`. Reuse these rather than building new setup.
- A "valuable" test asserts a branch or edge case not already covered — not a
  restatement of an existing happy-path test.

## Output contract

Emit findings that validate against `review-schema.json`: each finding carries
`location` (`path`, `line`), `issue`, `severity`, `suggested_fix`, and a stable
`detected_pattern` tag. On a re-run, `prior_findings.json` lists what was already
posted — report only **new or still-unaddressed** issues so the PR is not spammed
with duplicate comments on every push.
