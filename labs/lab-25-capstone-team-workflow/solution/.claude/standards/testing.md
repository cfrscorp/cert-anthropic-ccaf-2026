# Testing standards (imported module)

This file is not a CLAUDE.md itself. It is a focused standards document that
`.claude/CLAUDE.md` pulls in with `@standards/testing.md`, so the same rules can
be shared across memory files without duplication.

- Every module has a matching test (`test_<module>.py` for Python).
- Tests must be deterministic and run offline by default — no live network, no
  real clocks; mock them.
- Name test functions `test_<behavior>` so intent is obvious in the report.
- Prefer asserting on behavior, not incidental formatting.
- New behavior ships with a covering test in the same change.
