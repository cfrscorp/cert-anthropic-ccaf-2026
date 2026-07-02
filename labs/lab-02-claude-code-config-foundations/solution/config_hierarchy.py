#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Model the CLAUDE.md memory hierarchy and @import expansion (Task Statement 3.1).

Pure, filesystem-abstracted helpers so behavior is deterministic and testable:

- ``resolve_config`` merges the user / project / directory memory layers in the
  correct precedence order.
- ``resolve_imports`` expands ``@path`` import references (Claude Code's import
  syntax) against an in-memory ``{path: content}`` mapping.
- ``is_team_shared`` encodes the rule that user-level memory is NOT shared with
  teammates via version control.

Run ``uv run config_hierarchy.py --demo`` for a quick illustration.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys

__version__ = "1.0.0"

# Precedence order, least specific first. Later layers override earlier ones for
# overlapping instructions; all present layers are combined into the loaded
# context. (user-level ~/.claude/CLAUDE.md, project-level ./CLAUDE.md,
# directory-level subdir/CLAUDE.md)
LAYER_ORDER: tuple[str, ...] = ("user", "project", "directory")

# Which layers travel with the repository (version-controlled / team-shared).
_TEAM_SHARED = {"user": False, "project": True, "directory": True}

# A line that is exactly an import reference: ``@relative/path/to/file.md``.
_IMPORT_RE = re.compile(r"^\s*@(\S+)\s*$")


def is_team_shared(layer: str) -> bool:
    """Return True if a memory layer is shared with teammates via version control.

    User-level memory (``~/.claude/CLAUDE.md``) returns False: it applies only to
    the individual and is never committed, which is the root cause of the classic
    "new teammate isn't getting our rules" hierarchy bug.
    """
    if layer not in _TEAM_SHARED:
        raise ValueError(f"unknown layer {layer!r}; expected one of {LAYER_ORDER}")
    return _TEAM_SHARED[layer]


def resolve_config(layers: dict[str, str]) -> str:
    """Merge memory layers into a single loaded-context string, in precedence order.

    Args:
        layers: mapping of layer name -> markdown content. Recognized layer names
            are ``"user"``, ``"project"`` and ``"directory"``. Missing layers are
            simply omitted. Unknown keys raise ``ValueError``.

    Returns:
        The layers concatenated from least specific (user) to most specific
        (directory). More specific layers appear later so their instructions
        take precedence for anything that overlaps.
    """
    unknown = set(layers) - set(LAYER_ORDER)
    if unknown:
        raise ValueError(
            f"unknown layer(s) {sorted(unknown)}; expected subset of {LAYER_ORDER}"
        )

    sections: list[str] = []
    for layer in LAYER_ORDER:
        if layer not in layers:
            continue
        content = layers[layer].strip("\n")
        shared = "team-shared" if is_team_shared(layer) else "personal, not shared"
        sections.append(f"# [{layer} memory — {shared}]\n{content}")
    return "\n\n".join(sections)


def resolve_imports(path: str, files: dict[str, str], _seen: frozenset[str] | None = None) -> str:
    """Expand ``@path`` import references in ``files[path]`` recursively.

    Import targets are resolved relative to the importing file's directory, so
    ``@standards/testing.md`` inside ``CLAUDE.md`` resolves to
    ``standards/testing.md`` and ``@../../standards/testing.md`` inside
    ``src/api/CLAUDE.md`` resolves to ``standards/testing.md``.

    Args:
        path: key of the entry file within ``files``.
        files: mapping of normalized path -> file content.

    Returns:
        The file content with every ``@import`` line replaced by the expanded
        content of the referenced file.

    Raises:
        FileNotFoundError: an import target is not present in ``files``.
    """
    if path not in files:
        raise FileNotFoundError(f"import target not found: {path!r}")

    seen = _seen or frozenset()
    if path in seen:
        # Cycle guard: emit a marker instead of recursing forever.
        return f"<!-- circular import skipped: {path} -->"

    out_lines: list[str] = []
    for line in files[path].splitlines():
        m = _IMPORT_RE.match(line)
        if not m:
            out_lines.append(line)
            continue
        target = _resolve(path, m.group(1))
        out_lines.append(resolve_imports(target, files, seen | {path}))
    return "\n".join(out_lines)


def _resolve(importing_file: str, target: str) -> str:
    """Normalize an import target relative to the importing file's directory."""
    base_dir = posixpath.dirname(importing_file)
    return posixpath.normpath(posixpath.join(base_dir, target))


def _demo() -> str:
    files = {
        "CLAUDE.md": "# Project\nSee testing:\n@standards/testing.md\n",
        "standards/testing.md": "# Testing\n- deterministic tests only\n",
    }
    merged = resolve_config(
        {
            "user": "- personal: explain refactors first",
            "project": "- team: type hints everywhere",
            "directory": "- api: validate with Pydantic",
        }
    )
    expanded = resolve_imports("CLAUDE.md", files)
    return f"=== resolve_config ===\n{merged}\n\n=== resolve_imports ===\n{expanded}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config_hierarchy.py",
        description="Model the CLAUDE.md memory hierarchy and @import expansion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Show a worked demo of both helpers\n"
            "  uv run config_hierarchy.py --demo\n\n"
            "  # Print the version\n"
            "  uv run config_hierarchy.py --version\n"
        ),
    )
    parser.add_argument("--demo", action="store_true", help="print a worked example and exit")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.demo:
        print(_demo())
    else:
        print("Nothing to do. Try --demo or --help.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
