#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pick the right built-in tool for a task (Task Statement 2.5).

``choose_tool`` maps a plain-English task description to exactly one of the six
built-in Claude Code tools: Read, Write, Edit, Bash, Grep, Glob.

Selection criteria (from the exam guide):
- Grep  -> search file *contents* for a pattern (callers, error strings, imports)
- Glob  -> match file *paths* by name/extension pattern (e.g. **/*.test.tsx)
- Edit  -> targeted change anchored on unique text
- Write -> create/overwrite a whole file; also the fallback when Edit has no
           unique anchor text
- Read  -> load full file contents
- Bash  -> run a shell command (build, test, install, git)

Run ``uv run tool_selection.py "find all callers of process_order"``.
"""

from __future__ import annotations

import argparse
import re

__version__ = "1.0.0"

VALID_TOOLS = ("Read", "Write", "Edit", "Bash", "Grep", "Glob")


def choose_tool(task_description: str) -> str:
    """Return the single best built-in tool for ``task_description``.

    Rules are checked in priority order so overlapping keywords resolve the way
    Task Statement 2.5 describes. Raises ``ValueError`` when nothing matches.
    """
    t = task_description.lower()

    # 1) Edit-failure fallback -> Write. Checked first because these phrases also
    #    contain "unique"/"edit", which later rules key on.
    if _any(t, ["edit failed", "no unique", "not unique", "non-unique", "isn't unique",
                "multiple matches", "ambiguous", "fallback"]):
        return "Write"

    # 2) Glob -> matching files by path/name/extension pattern. Requires a
    #    file-oriented cue so it wins over Grep's generic "find" verbs.
    if _any(t, ["glob", "**/", "*.", "file name", "filename", "by name",
                "by extension", "file path pattern", "path pattern",
                "files matching", "files named", "matching pattern"]):
        return "Glob"

    # 3) Grep -> search inside file contents.
    if _any(t, ["grep", "caller", "search", "find all", "occurrence", "references to",
                "usages of", "where is", "used", "error message", "function name",
                "import statement", "string in", "search contents", "content search"]):
        return "Grep"

    # 4) Write -> create or overwrite a whole file.
    if _any(t, ["create a file", "new file", "overwrite", "write a file",
                "write the file", "generate a file", "create file"]):
        return "Write"

    # 5) Edit -> targeted, unique-anchored modification.
    if _any(t, ["unique", "edit", "modify", "change a line", "change the line",
                "replace", "targeted", "single line", "one line", "tweak"]):
        return "Edit"

    # 6) Bash -> run a command.
    if _any(t, ["run ", "execute", "command", "shell", "test suite", "run tests",
                "install", "build", "git ", "npm", "pytest"]):
        return "Bash"

    # 7) Read -> load full file contents.
    if _any(t, ["read", "open the file", "view", "full file", "file contents",
                "load the file", "inspect the file"]):
        return "Read"

    raise ValueError(f"could not determine a tool for: {task_description!r}")


def _any(haystack: str, needles: list[str]) -> bool:
    return any(n in haystack for n in needles)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool_selection.py",
        description="Pick the right built-in Claude Code tool for a task.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Content search across the codebase -> Grep\n"
            '  uv run tool_selection.py "find all callers of process_order"\n\n'
            "  # File path pattern -> Glob\n"
            '  uv run tool_selection.py "find files matching **/*.test.tsx"\n\n'
            "  # Targeted unique edit -> Edit\n"
            '  uv run tool_selection.py "modify a unique line in config.py"\n\n'
            "  # Edit had no unique anchor -> Write fallback\n"
            '  uv run tool_selection.py "Edit failed, no unique anchor text"\n\n'
            "  uv run tool_selection.py --version\n"
        ),
    )
    parser.add_argument(
        "task", nargs="?", help="plain-English description of the task"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
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
