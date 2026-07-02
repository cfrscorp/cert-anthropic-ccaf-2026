---
name: analyze-codebase
# TODO: this frontmatter is INCOMPLETE and will fail validate_skill_frontmatter.
# Fix it so the skill:
#   - has a non-empty `description`
#   - runs forked:            context: fork
#   - is read-only:           allowed-tools: Read, Grep, Glob
#   - prompts for an arg:     argument-hint: "[directory or subsystem]"
# Remove any keys that are not in the allowed set.
context: forked            # TODO: wrong value — should be "fork"
tools: Read, Grep, Glob    # TODO: wrong key — should be "allowed-tools"
---

# analyze-codebase

TODO: write the skill body — inventory structure with Glob, find entry points
with Grep, follow key files with Read, then return ONLY a concise structured
summary to the main session.
