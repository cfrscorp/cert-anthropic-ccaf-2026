# Sample Project — Project Memory (project-level)

This file lives at the repository root. It is committed to version control, so
**every teammate who clones the repo gets these instructions automatically.**
This is the project-level layer of the CLAUDE.md hierarchy.

## Coding standards

- Use type hints on all public functions.
- Prefer pure functions; push I/O to the edges of the system.
- Keep functions small and single-purpose.

## Testing

The testing conventions are kept in a separate file and pulled in with an
`@import` reference so they can be reused by other memory files:

@standards/testing.md
