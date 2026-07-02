---
name: api
description: Conventions for HTTP API handlers under src/api.
paths:
  - "src/api/**/*"
---

# API handler conventions

Loaded only when editing files under `src/api/`.

- Handlers are `async` functions using `async/await`; never mix in raw promises.
- Validate every request body with a Zod schema before touching the database.
- Wrap handler bodies in the shared `withErrorBoundary()` helper so failures map
  to structured `{ error, code }` JSON responses, never raw stack traces.
- Return typed results; do not `res.send(anyObject)` without a response schema.
- Log at the boundary with the request id; never log secrets or tokens.
