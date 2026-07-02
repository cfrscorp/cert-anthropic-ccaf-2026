---
paths: ["**/test_*.py", "**/*.test.tsx"]
---

# Testing rules (path-scoped)

This is the `.claude/rules/` alternative to a monolithic CLAUDE.md. Because the
`paths` frontmatter uses glob patterns, these rules load **only** when you are
editing a matching test file — regardless of which directory it lives in. That
is the key advantage over a directory-level CLAUDE.md, which can only cover one
directory subtree.

- One behavior per test function.
- No network access in unit tests.
- Prefer fixtures over ad-hoc setup.
