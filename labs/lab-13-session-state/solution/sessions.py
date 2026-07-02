"""Reference solution for L13 — Session State, Resumption & Forking.

A small, dependency-free ``SessionStore`` that models the SDK's session
behavior offline so the concepts from Task Statement 1.7 can be exercised
deterministically:

* ``save`` / ``resume`` — persist a named conversation and continue it later,
  the moral equivalent of ``--resume <session-name>``.
* ``fork`` — branch a saved session into an INDEPENDENT copy (a shared analysis
  baseline you can take in divergent directions). Mutating the fork must never
  touch the original, so we deep-copy on the way out.
* ``should_resume`` — the resume-vs-restart-with-summary decision: resuming is
  cheap when prior context is still valid, but stale tool results make a fresh
  session seeded with a structured summary more reliable.
* ``inject_file_change_notice`` — when you DO resume after code changed, tell the
  agent exactly which files moved so it re-analyzes them instead of trusting a
  stale reading (or re-exploring everything from scratch).

The store is backed by an optional JSON file so state survives across process
runs, mirroring how named sessions persist on disk. With no path it stays purely
in memory.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

__all__ = [
    "SessionStore",
    "should_resume",
    "inject_file_change_notice",
]

Message = dict[str, Any]


class SessionStore:
    """An in-memory / JSON-file-backed store of named conversation sessions.

    Each session name maps to a list of message dicts (the conversation
    history). This deliberately mirrors the SDK's named-session model so the
    resume / fork semantics can be practiced without a live agent.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        """Create a store, optionally persisted to ``path`` (a JSON file).

        With ``path`` set, every mutation is flushed to disk and existing state
        is loaded on construction, so a later process can ``resume`` a session
        saved earlier. With ``path=None`` the store lives only in memory.
        """
        self.path = Path(path) if path is not None else None
        self._sessions: dict[str, list[Message]] = {}
        if self.path is not None and self.path.exists():
            self._sessions = json.loads(self.path.read_text(encoding="utf-8"))

    # -- persistence ------------------------------------------------------
    def _flush(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._sessions, indent=2), encoding="utf-8"
            )

    # -- core API ---------------------------------------------------------
    def save(self, name: str, messages: list[Message]) -> None:
        """Store ``messages`` under session ``name`` (overwriting any prior).

        A deep copy is stored so later mutation of the caller's list cannot
        retroactively change saved history.
        """
        self._sessions[name] = copy.deepcopy(messages)
        self._flush()

    def resume(self, name: str) -> list[Message]:
        """Return a fresh copy of the prior history for session ``name``.

        This is the ``--resume <session-name>`` analogue: you get the recorded
        conversation back so you can append new turns and continue. A copy is
        returned so callers mutate their working history, not the stored one.
        """
        if name not in self._sessions:
            raise KeyError(f"No session named {name!r}. Known: {self.list_sessions()}")
        return copy.deepcopy(self._sessions[name])

    def fork(self, name: str, new_name: str) -> str:
        """Branch session ``name`` into an INDEPENDENT session ``new_name``.

        This models ``fork_session``: both branches start from the same analysis
        baseline, but diverge freely. The fork is a DEEP COPY, so appending to
        (or otherwise mutating) either branch never affects the other. Returns
        ``new_name`` for convenient chaining.
        """
        if name not in self._sessions:
            raise KeyError(f"No session named {name!r}. Known: {self.list_sessions()}")
        if new_name in self._sessions:
            raise ValueError(f"Session {new_name!r} already exists; pick a new name.")
        self._sessions[new_name] = copy.deepcopy(self._sessions[name])
        self._flush()
        return new_name

    def list_sessions(self) -> list[str]:
        """Return the known session names, sorted for stable output."""
        return sorted(self._sessions)


def should_resume(prior_results_stale: bool) -> str:
    """Choose between resuming and starting fresh with a structured summary.

    Returns ``"resume"`` when the prior context is still valid (cheap, keeps the
    full conversation), and ``"restart_with_summary"`` when prior tool results
    are stale — a new session seeded with a hand-written structured summary is
    more reliable than resuming on top of results that no longer reflect reality.
    """
    return "restart_with_summary" if prior_results_stale else "resume"


def inject_file_change_notice(
    messages: list[Message], changed_files: list[str]
) -> list[Message]:
    """Append a targeted re-analysis notice naming the ``changed_files``.

    When you resume a session after modifying files the agent already read, its
    memory of those files is stale. Rather than forcing a full re-exploration,
    inject a user turn that names exactly what changed so the agent re-reads only
    those files. Returns a NEW list (the input is not mutated); an empty
    ``changed_files`` list is a no-op and returns a copy unchanged.
    """
    result = copy.deepcopy(messages)
    if not changed_files:
        return result
    file_list = ", ".join(changed_files)
    notice = (
        "The following files changed since this session was last active: "
        f"{file_list}. Re-analyze only these files before continuing; treat any "
        "earlier analysis of them as stale."
    )
    result.append({"role": "user", "content": notice})
    return result
