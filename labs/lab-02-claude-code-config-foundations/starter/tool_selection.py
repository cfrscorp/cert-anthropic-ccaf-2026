#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pick the right built-in tool for a task (Task Statement 2.5).

TODO(learner): implement ``choose_tool`` so it returns exactly one of
VALID_TOOLS for each canonical task. See README.md for the mapping.

Run tests from ``labs/``:  uv run pytest lab-02-claude-code-config-foundations -q
"""

from __future__ import annotations

import argparse

__version__ = "1.0.0"

VALID_TOOLS = ("Read", "Write", "Edit", "Bash", "Grep", "Glob")


def choose_tool(task_description: str) -> str:
    """Return the single best built-in tool for ``task_description``.

    Selection criteria (Task Statement 2.5):
    - Grep  -> search file contents (callers, error strings, imports)
    - Glob  -> match file paths by name/extension (e.g. **/*.test.tsx)
    - Edit  -> targeted change anchored on unique text
    - Write -> create/overwrite a file; fallback when Edit has no unique anchor
    - Read  -> load full file contents
    - Bash  -> run a shell command

    Raise ValueError when nothing matches.
    """
    # TODO(learner): inspect task_description (case-insensitive) and return one
    # of VALID_TOOLS. Order your checks so the Edit-failure fallback and Glob
    # patterns are handled before generic "find"/"edit" keywords.
    raise NotImplementedError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool_selection.py",
        description="Pick the right built-in Claude Code tool for a task.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  uv run tool_selection.py "find all callers of process_order"\n'
            '  uv run tool_selection.py "find files matching **/*.test.tsx"\n'
            "  uv run tool_selection.py --version\n"
        ),
    )
    parser.add_argument("task", nargs="?", help="plain-English description of the task")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.task:
        _build_parser().print_help()
        return 0
    print(choose_tool(args.task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
