"""Starter scaffold for L16 — Task Decomposition & Multi-pass Review.

Implement the functions below, keeping the same public API as ``solution/``.
Run the tests from the ``labs/`` directory:

    uv run pytest lab-16-decomposition-and-review

This module encodes two exam ideas:

* Task Statement 1.6 — choose FIXED sequential pipelines (prompt chaining) for
  predictable multi-aspect work, and DYNAMIC adaptive decomposition for
  open-ended investigation whose subtasks emerge from what you discover.
* Task Statement 4.6 — split large reviews into one local pass per file plus a
  single cross-file integration pass; prefer an INDEPENDENT review instance over
  self-review; and route findings by self-reported confidence.

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

__all__ = [
    "choose_decomposition",
    "plan_review_passes",
    "is_independent_review",
    "route_by_confidence",
    "independent_second_pass",
    "DEFAULT_MODEL",
]

# Model id passed through to the injected client. The MockAnthropic client used
# in tests ignores it; it exists so real callers can override it.
DEFAULT_MODEL = "claude-sonnet-4-5"


def choose_decomposition(task: dict) -> str:
    """Return the decomposition strategy for ``task``.

    Return ``"prompt_chaining"`` for predictable, multi-aspect work whose full
    set of subtasks can be enumerated up front (e.g. "review each of these 14
    files, then run a cross-file integration pass").

    Return ``"dynamic"`` for open-ended investigation whose subtasks are
    generated from intermediate findings (e.g. "add comprehensive tests to a
    legacy codebase" — you must first map structure, find high-impact areas,
    then adapt the plan as dependencies are discovered).

    TODO: implement. Consider an explicit ``open_ended`` flag, a known ``type``,
    and keyword signals in the task's goal/description text.
    """
    raise NotImplementedError("Implement choose_decomposition")


def plan_review_passes(files: list[str]) -> list[dict]:
    """Plan a multi-pass review over ``files``.

    Return exactly one LOCAL pass per file (focused on issues within that single
    file) plus EXACTLY ONE integration pass (cross-file data flow). For N files
    the result has N + 1 entries, the last being the integration pass.

    TODO: implement. Give each pass enough metadata for a caller to run it
    (e.g. kind, scope, the file(s) it covers, a focus description).
    """
    raise NotImplementedError("Implement plan_review_passes")


def is_independent_review(review_context: dict) -> bool:
    """Return whether a review is INDEPENDENT of the code's generation.

    Return ``False`` when the reviewer shares the generator's reasoning context
    (self-review in the same session) and ``True`` for a fresh instance that
    never saw the generation reasoning.

    TODO: implement. Compare the generator vs reviewer sessions, or honour an
    explicit ``shares_reasoning_context`` flag.
    """
    raise NotImplementedError("Implement is_independent_review")


def route_by_confidence(findings: list[dict], threshold: float) -> dict:
    """Partition ``findings`` by each finding's self-reported ``confidence``.

    Findings at or above ``threshold`` route to ``"auto"``; everything below
    (and anything missing a confidence) routes to ``"human_review"``.

    TODO: implement. Return a dict with ``"auto"`` and ``"human_review"`` lists.
    """
    raise NotImplementedError("Implement route_by_confidence")


def independent_second_pass(client, review_target: dict, *, model: str = DEFAULT_MODEL) -> list[dict]:
    """Run a review with a fresh Claude instance and return its findings.

    ``client`` is injected (dependency injection) so tests can pass a mock. The
    point of this function is that ``client`` carries NONE of the generator's
    conversation history — that is what makes the review independent (4.6).

    ``review_target`` is ``{"file": <name>, "code": <source>}``. Drive the model
    with a ``report_finding`` tool (``tool_choice`` = ``{"type": "any"}``) and
    return a list of finding dicts parsed from its tool calls.

    TODO: implement.
    """
    raise NotImplementedError("Implement independent_second_pass")
