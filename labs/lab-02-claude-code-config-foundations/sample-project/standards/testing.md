# Testing standards (imported module)

This file is not a CLAUDE.md itself. It is a focused standards document that
CLAUDE.md files pull in with `@import`, so the same rules can be shared by the
project root and by individual packages without copy/paste.

- Every module has a matching `test_<module>.py`.
- Tests must be deterministic and run offline by default.
- Name test functions `test_<behavior>` so intent is obvious from the report.
- Prefer asserting on behavior, not on incidental formatting.
