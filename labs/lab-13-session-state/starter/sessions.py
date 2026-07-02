"""Starter scaffold for L13 — Session State, Resumption & Forking.

Implement a small ``SessionStore`` plus two helper functions that model the
SDK's named-session behavior from Task Statement 1.7. See README.md for the full
brief. The public API here MUST match ``solution/sessions.py`` so the same tests
run against both.

Key semantics to get right:

* ``resume`` returns the PRIOR history so a session can be continued.
* ``fork`` creates an INDEPENDENT branch — mutating the fork must NOT change the
  original baseline. (Hint: deep copy.)
* ``should_resume`` returns ``"restart_with_summary"`` when prior tool results
  are stale, else ``"resume"``.
* ``inject_file_change_notice`` appends a re-analysis notice naming the changed
  files, without mutating the caller's list.

Run the tests from the ``labs/`` directory:  uv run pytest lab-13-session-state
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "SessionStore",
    "should_resume",
    "inject_file_change_notice",
]

Message = dict[str, Any]


class SessionStore:
    """An in-memory / JSON-file-backed store of named conversation sessions."""

    def __init__(self, path: str | Path | None = None) -> None:
        """Create a store, optionally persisted to the JSON file ``path``."""
        # TODO: keep an optional Path and a dict {name -> list[messages]}.
        # TODO: if path exists, load prior state from it (JSON).
        raise NotImplementedError("Implement SessionStore.__init__ (see README.md).")

    def save(self, name: str, messages: list[Message]) -> None:
        """Store ``messages`` under session ``name`` (deep-copied)."""
        # TODO: store a deep copy under `name`; flush to disk if a path is set.
        raise NotImplementedError("Implement SessionStore.save (see README.md).")

    def resume(self, name: str) -> list[Message]:
        """Return a fresh copy of the prior history for session ``name``."""
        # TODO: raise KeyError if unknown; else return a deep copy of the history.
        raise NotImplementedError("Implement SessionStore.resume (see README.md).")

    def fork(self, name: str, new_name: str) -> str:
        """Branch session ``name`` into an INDEPENDENT session ``new_name``."""
        # TODO: deep-copy the baseline into `new_name` so the branches are
        # independent; return `new_name`.
        raise NotImplementedError("Implement SessionStore.fork (see README.md).")

    def list_sessions(self) -> list[str]:
        """Return the known session names (sorted)."""
        # TODO: return the session names, sorted.
        raise NotImplementedError("Implement SessionStore.list_sessions (see README.md).")


def should_resume(prior_results_stale: bool) -> str:
    """Return "restart_with_summary" when stale, else "resume"."""
    # TODO: pick resume vs restart_with_summary based on staleness.
    raise NotImplementedError("Implement should_resume (see README.md).")


def inject_file_change_notice(
    messages: list[Message], changed_files: list[str]
) -> list[Message]:
    """Append a targeted re-analysis notice naming the ``changed_files``."""
    # TODO: return a NEW list; if changed_files is non-empty, append a user turn
    # naming exactly those files so the agent re-analyzes only them.
    raise NotImplementedError("Implement inject_file_change_notice (see README.md).")
