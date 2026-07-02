# API package memory (directory-level)

This file lives in `src/api/`. Claude loads it **in addition to** the project
root `CLAUDE.md` when you are working inside this directory. Because it is more
specific, its instructions take precedence over the project root for any
overlapping rules — this is the directory-level layer of the hierarchy.

## API conventions

- All endpoints validate input with Pydantic models.
- Return typed responses; never leak raw exceptions to clients.
- Version every breaking change under a new path prefix (e.g. `/v2/...`).

## Testing for this package

Reuse the shared testing standards via a relative `@import` so we do not
duplicate them here:

@../../standards/testing.md
