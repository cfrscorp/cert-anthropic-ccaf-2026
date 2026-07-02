#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Model the CLAUDE.md memory hierarchy and @import expansion (Task Statement 3.1).

TODO(learner): implement the three functions below so the tests pass. They must
be pure (no real filesystem access) — the "filesystem" is passed in as a dict.

Run tests from ``labs/``:  uv run pytest lab-02-claude-code-config-foundations -q
"""

from __future__ import annotations

import argparse
import posixpath  # noqa: F401  (you'll likely want this for import resolution)
import re  # noqa: F401
import sys

__version__ = "1.0.0"

# Precedence order, least specific first. Later layers override earlier ones.
LAYER_ORDER: tuple[str, ...] = ("user", "project", "directory")


def is_team_shared(layer: str) -> bool:
    """Return True if a memory layer is shared with teammates via version control.

    User-level memory (``~/.claude/CLAUDE.md``) is NOT shared; project- and
    directory-level memory live in the repo and are shared.
    """
    # TODO(learner): return False for "user"; True for "project"/"directory";
    # raise ValueError for anything else.
    raise NotImplementedError


def resolve_config(layers: dict[str, str]) -> str:
    """Merge memory layers into one string, least specific (user) first.

    More specific layers appear later so they take precedence for overlaps.
    Missing layers are omitted; unknown layer names raise ValueError.
    """
    # TODO(learner): iterate LAYER_ORDER, skip missing layers, join with blank
    # lines. Label each section so precedence is visible in the output.
    raise NotImplementedError


def resolve_imports(path: str, files: dict[str, str], _seen=None) -> str:
    """Expand ``@path`` import references in ``files[path]`` recursively.

    Import targets resolve relative to the importing file's directory. Raise
    FileNotFoundError when a target is missing; guard against import cycles.
    """
    # TODO(learner): for each line, if it is exactly ``@<path>``, resolve the
    # path relative to `path`'s directory and recurse; otherwise keep the line.
    raise NotImplementedError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config_hierarchy.py",
        description="Model the CLAUDE.md memory hierarchy and @import expansion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run config_hierarchy.py --demo\n"
            "  uv run config_hierarchy.py --version\n"
        ),
    )
    parser.add_argument("--demo", action="store_true", help="print a worked example and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.demo:
        print(resolve_config({"project": "- type hints everywhere"}))
    else:
        print("Nothing to do. Try --demo or --help.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
