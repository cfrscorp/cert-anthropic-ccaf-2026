"""Starter scaffold for L14 — Context Management & Preservation.

Implement four context-engineering primitives that keep critical information
alive across long agent sessions (Task Statements 5.1 and 5.4). Each function
and method below currently raises ``NotImplementedError``; replace the bodies
so the public API matches ``solution/context.py`` and the tests pass.

Public API (do not rename):

    extract_case_facts(conversation) -> dict
    trim_tool_output(raw, relevant_fields) -> dict
    order_for_position(sections, *, summary_header="Key Findings") -> list
    class Scratchpad: record(key, value); recall(key)
    load_manifest(path) -> dict

Run the tests from the ``labs/`` directory:  uv run pytest lab-14-context-management
See README.md for the full walkthrough.
"""

from __future__ import annotations

import os
from typing import Any

__all__ = [
    "extract_case_facts",
    "trim_tool_output",
    "order_for_position",
    "Scratchpad",
    "load_manifest",
]


def extract_case_facts(conversation: list[Any]) -> dict[str, list[str]]:
    """Extract transactional facts into a persistent, structured case-facts block.

    Scan every message and pull out the values a progressive summary would
    lose: dollar amounts, dates, order numbers, and statuses. Return a dict
    with keys ``amounts``, ``dates``, ``order_numbers`` and ``statuses``, each
    a list of de-duplicated string values in first-seen order.

    Hints:
      - Messages may be plain strings or dicts with a ``content`` field (which
        may itself be a string or a list of content blocks).
      - Use regular expressions for amounts (``$129.99``), ISO dates
        (``2026-06-15``) and order ids (``A-10432``); match statuses against a
        known vocabulary (shipped, delivered, in transit, refund, ...).
    """
    raise NotImplementedError("Implement extract_case_facts (see README.md).")


def trim_tool_output(raw: dict[str, Any], relevant_fields: list[str]) -> dict[str, Any]:
    """Trim a verbose tool result down to only the fields the agent needs.

    Return a new dict containing only the requested top-level keys that exist
    in ``raw``, in the order given by ``relevant_fields``. Keys absent from
    ``raw`` should be skipped, not raised on.
    """
    raise NotImplementedError("Implement trim_tool_output (see README.md).")


def order_for_position(
    sections: list[dict[str, Any]],
    *,
    summary_header: str = "Key Findings",
) -> list[dict[str, str]]:
    """Order sections so a key-findings summary comes FIRST, details after.

    Build a list of ``{"header", "body"}`` dicts where element 0 is a summary
    section (header ``summary_header``) whose body lists each section's
    ``title`` and ``summary``, followed by one entry per detailed section
    (header = ``title``, body = ``detail``). This mitigates the
    "lost in the middle" effect.
    """
    raise NotImplementedError("Implement order_for_position (see README.md).")


class Scratchpad:
    """A crash-recoverable key/value scratchpad backed by a JSON file.

    ``record`` must flush state to disk so a *fresh* ``Scratchpad`` pointed at
    the same path can ``recall`` it. Load any existing file in ``__init__``.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        # TODO: store the path and load any existing JSON state from disk.
        self.path = path

    def record(self, key: str, value: Any) -> None:
        """Record ``value`` under ``key`` and flush to disk immediately."""
        raise NotImplementedError("Implement Scratchpad.record (see README.md).")

    def recall(self, key: str, default: Any = None) -> Any:
        """Return the value stored under ``key`` (or ``default`` if absent)."""
        raise NotImplementedError("Implement Scratchpad.recall (see README.md).")


def load_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a structured state manifest (JSON) from ``path`` and return it."""
    raise NotImplementedError("Implement load_manifest (see README.md).")
