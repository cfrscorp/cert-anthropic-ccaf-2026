---
name: testing
description: Conventions for all test files, wherever they live in the tree.
paths:
  - "**/*.test.tsx"
  - "**/*.test.ts"
---

# Testing conventions

These rules load automatically whenever you edit a test file, regardless of
which directory it lives in. Because test files are scattered next to the code
they cover (`Button.test.tsx` beside `Button.tsx`), a glob-scoped rule is more
maintainable than a per-directory `CLAUDE.md`.

- Use Vitest with `describe` / `it`; one top-level `describe` per unit under test.
- Name tests as behavior statements: `it("returns [] when no rule matches")`.
- Arrange–Act–Assert with a blank line between the three sections.
- Prefer `screen.getByRole` over `getByTestId` in React Testing Library.
- No network or real timers — mock them; tests must be deterministic and offline.
