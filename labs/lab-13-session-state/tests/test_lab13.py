"""Deterministic tests for L13 — Session State, Resumption & Forking.

These exercise the session semantics from Task Statement 1.7:
save+resume round-trips history, fork produces an INDEPENDENT branch, the
resume-vs-restart-with-summary decision keys off stale tool results, and a
resumed session can be told exactly which files changed.

Run from labs/:  uv run pytest lab-13-session-state
Validate ref:     LAB_TARGET=solution uv run pytest lab-13-session-state
"""

from __future__ import annotations

import pytest
from labkit import lab_module

sessions = lab_module(__file__, "sessions")


BASELINE = [
    {"role": "user", "content": "Analyze the auth module."},
    {"role": "assistant", "content": "Found 3 handlers in auth.py."},
]


def test_save_then_resume_returns_same_history(tmp_path):
    """resume() gives back exactly what save() stored."""
    store = sessions.SessionStore(tmp_path / "sessions.json")
    store.save("audit", BASELINE)

    resumed = store.resume("audit")
    assert resumed == BASELINE


def test_resume_persists_across_store_instances(tmp_path):
    """A JSON-backed store can be resumed from a fresh process/instance."""
    path = tmp_path / "sessions.json"
    sessions.SessionStore(path).save("audit", BASELINE)

    # A brand-new store pointed at the same file must see the saved session.
    reopened = sessions.SessionStore(path)
    assert reopened.list_sessions() == ["audit"]
    assert reopened.resume("audit") == BASELINE


def test_fork_creates_independent_copy(tmp_path):
    """Mutating a fork must NOT affect the original baseline."""
    store = sessions.SessionStore(tmp_path / "sessions.json")
    store.save("baseline", BASELINE)

    store.fork("baseline", "approach_a")

    # Diverge the fork: continue it with a new turn.
    forked = store.resume("approach_a")
    forked.append({"role": "user", "content": "Try a mock-based test strategy."})
    store.save("approach_a", forked)

    # The original baseline is untouched.
    assert store.resume("baseline") == BASELINE
    assert len(store.resume("approach_a")) == len(BASELINE) + 1
    assert {"baseline", "approach_a"}.issubset(set(store.list_sessions()))


def test_fork_deep_copies_nested_structures(tmp_path):
    """Independence must be deep: nested content isn't shared with the original."""
    store = sessions.SessionStore(tmp_path / "sessions.json")
    nested = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
    store.save("base", nested)
    store.fork("base", "branch")

    branch = store.resume("branch")
    branch[0]["content"][0]["text"] = "MUTATED"
    store.save("branch", branch)

    # The baseline's nested block is unchanged.
    assert store.resume("base")[0]["content"][0]["text"] == "hi"


def test_should_resume_restart_when_stale():
    """Stale prior tool results -> start fresh with a structured summary."""
    assert sessions.should_resume(prior_results_stale=True) == "restart_with_summary"


def test_should_resume_resume_when_fresh():
    """Prior context still valid -> resume the existing session."""
    assert sessions.should_resume(prior_results_stale=False) == "resume"


def test_inject_file_change_notice_references_changed_files():
    """The injected notice names exactly the files that changed."""
    changed = ["auth.py", "db/models.py"]
    updated = sessions.inject_file_change_notice(BASELINE, changed)

    # A turn was appended and the original list is untouched.
    assert len(updated) == len(BASELINE) + 1
    assert len(BASELINE) == 2

    notice = updated[-1]
    assert notice["role"] == "user"
    for f in changed:
        assert f in notice["content"]


def test_inject_file_change_notice_empty_is_noop():
    """No changed files -> nothing appended (a copy of the input)."""
    updated = sessions.inject_file_change_notice(BASELINE, [])
    assert updated == BASELINE
