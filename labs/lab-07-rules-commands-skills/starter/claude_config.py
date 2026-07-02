"""Starter: parsing and validating Claude Code configuration.

Implement the three public functions below. They are pure — no Claude calls, no
filesystem coupling. Callers read the files and pass text/dicts in.

The functions model the three project-scoped configuration mechanisms in this
lab:

- ``.claude/rules/*.md``    — path-conditional convention files (YAML frontmatter
  with a ``paths:`` list of globs). Loaded only when editing a matching file.
- ``.claude/commands/*.md``  — project-scoped slash commands (shared via git).
- ``.claude/skills/<name>/SKILL.md`` — on-demand skills whose frontmatter may set
  ``context: fork``, ``allowed-tools``, and ``argument-hint``.

pyyaml is available (``import yaml``) for parsing frontmatter.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-07-rules-commands-skills -q
"""

from __future__ import annotations

# You will likely want these:
# import re
# import yaml


def parse_frontmatter(markdown_text: str) -> dict:
    """Extract the leading YAML frontmatter block from a markdown document.

    Frontmatter is the block delimited by a line of ``---`` at the very top of
    the file and a closing ``---`` line. Return the parsed mapping, or ``{}``
    when there is no frontmatter (or it is empty / not a mapping).

    TODO:
      1. If the text does not start with ``---`` (ignoring a leading BOM / blank
         lines), return {}.
      2. Find the closing ``---`` line. If there isn't one, return {}.
      3. yaml.safe_load the lines between the fences.
      4. Return the mapping (or {} if the parsed value isn't a dict).
    """
    raise NotImplementedError("TODO: implement parse_frontmatter()")


def rules_for_path(path: str, rules: list[dict]) -> list[str]:
    """Names of the rules whose ``paths`` globs match ``path``.

    Each rule is a mapping with a ``name`` and a ``paths`` list, e.g.::

        {"name": "testing", "paths": ["**/*.test.tsx", "**/*.test.ts"]}

    A rule matches if ANY of its globs matches the path.

    TODO:
      1. Implement a glob matcher that handles ``**`` crossing directory
         boundaries: ``**/*.test.tsx`` must match ``src/ui/Button.test.tsx`` AND
         ``Button.test.tsx``; ``src/api/**/*`` must match ``src/api/users.ts``
         AND ``src/api/v1/handlers.ts``. Plain fnmatch is NOT enough — translate
         the glob to a regex, or use another ``**``-aware matcher.
      2. Return the ``name`` of every rule that has at least one matching glob.
      3. A path matching no rule returns [].
    """
    raise NotImplementedError("TODO: implement rules_for_path()")


def validate_skill_frontmatter(fm: dict) -> list[str]:
    """Validate a SKILL.md frontmatter mapping; return a list of problems.

    An empty list means the frontmatter is valid.

    TODO — flag each of these as a problem string (return them all):
      - ``description`` missing or empty.
      - any key outside {name, description, context, allowed-tools, argument-hint}.
      - ``context`` present but not equal to "fork".
      - ``allowed-tools`` present but not a non-empty list / comma-separated string.
      - ``argument-hint`` present but empty.
    Return [] when the frontmatter satisfies all of the above.
    """
    raise NotImplementedError("TODO: implement validate_skill_frontmatter()")
