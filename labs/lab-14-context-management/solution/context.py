"""Reference solution for L14 — Context Management & Preservation.

This module implements four context-engineering primitives that keep critical
information alive across long agent sessions (Task Statements 5.1 and 5.4):

* ``extract_case_facts`` — pull transactional facts (amounts, dates, order
  numbers, statuses) out of the raw conversation into a compact, structured
  "case facts" block that can be re-injected into every prompt *outside* the
  summarized history. Progressive summarization tends to blur exactly these
  values ("about $130", "sometime in June"); a facts block preserves them
  verbatim.
* ``trim_tool_output`` — keep only the handful of fields an agent actually
  needs from a verbose tool result (e.g. 40+ fields from an order lookup down
  to 5). Verbose tool results accumulate in context and consume tokens
  disproportionately to their relevance.
* ``order_for_position`` — place a key-findings summary FIRST and the detailed
  sections after it, each behind an explicit header, to mitigate the
  "lost in the middle" effect (models process the beginning and end of a long
  input reliably but drop content buried in the middle).
* ``Scratchpad`` + ``load_manifest`` — persist key findings and structured
  agent state to a JSON file that survives a crash or a fresh process, so a
  coordinator can resume by loading a manifest rather than re-exploring.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

__all__ = [
    "extract_case_facts",
    "trim_tool_output",
    "order_for_position",
    "Scratchpad",
    "load_manifest",
]

# --- extraction patterns ---------------------------------------------------

# "$129.99", "$45.50", "$1,299"
_AMOUNT_RE = re.compile(r"\$\d[\d,]*(?:\.\d{2})?")
# ISO 8601 (2026-06-15) and US slash (06/15/2026)
_DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b")
# Order ids like A-10432, ORD-77219 (letters, a dash, then >=3 digits)
_ORDER_RE = re.compile(r"\b[A-Z]{1,4}-\d{3,}\b")
# Known status vocabulary, matched case-insensitively as substrings. Longer
# phrases come first so "out for delivery" wins over a bare "delivery".
_STATUS_TERMS = [
    "out for delivery",
    "in transit",
    "backordered",
    "processing",
    "delivered",
    "shipped",
    "cancelled",
    "canceled",
    "refunded",
    "refund",
    "returned",
    "pending",
]


def _dedupe(seq: list[str]) -> list[str]:
    """Return ``seq`` with duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _message_text(message: Any) -> str:
    """Best-effort extraction of the text of a single conversation message."""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        # Content blocks: [{"type": "text", "text": "..."}, ...]
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(str(block["text"]))
                elif isinstance(block, str):
                    parts.append(block)
            return " ".join(parts)
    return ""


def extract_case_facts(conversation: list[Any]) -> dict[str, list[str]]:
    """Extract transactional facts into a persistent, structured case-facts block.

    Scans every message in ``conversation`` and pulls out the values that a
    progressive summary would most likely lose: dollar amounts, dates, order
    numbers, and statuses. Values are returned verbatim, de-duplicated, in the
    order they first appear.

    Args:
        conversation: a list of messages. Each message may be a plain string,
            or a dict with a ``content`` field that is either a string or a
            list of content blocks.

    Returns:
        A dict with keys ``amounts``, ``dates``, ``order_numbers`` and
        ``statuses``, each mapping to a list of the extracted string values.
    """
    amounts: list[str] = []
    dates: list[str] = []
    orders: list[str] = []
    statuses: list[str] = []

    for message in conversation:
        text = _message_text(message)
        if not text:
            continue
        amounts.extend(_AMOUNT_RE.findall(text))
        dates.extend(_DATE_RE.findall(text))
        orders.extend(_ORDER_RE.findall(text))
        lowered = text.lower()
        for term in _STATUS_TERMS:
            if term in lowered:
                statuses.append(term)

    return {
        "amounts": _dedupe(amounts),
        "dates": _dedupe(dates),
        "order_numbers": _dedupe(orders),
        "statuses": _dedupe(statuses),
    }


def trim_tool_output(raw: dict[str, Any], relevant_fields: list[str]) -> dict[str, Any]:
    """Trim a verbose tool result down to only the fields the agent needs.

    Verbose tool outputs (an order lookup can return 40+ fields) accumulate in
    context and cost tokens out of proportion to their usefulness. Keep only
    the requested fields *before* the result enters conversation history.

    Args:
        raw: the full tool result.
        relevant_fields: the top-level keys to keep. Keys absent from ``raw``
            are silently skipped (so callers can request a stable field set).

    Returns:
        A new dict containing only the requested keys that exist in ``raw``,
        in the order given by ``relevant_fields``.
    """
    return {field: raw[field] for field in relevant_fields if field in raw}


def order_for_position(
    sections: list[dict[str, Any]],
    *,
    summary_header: str = "Key Findings",
) -> list[dict[str, str]]:
    """Order sections so a key-findings summary comes FIRST, details after.

    Mitigates the "lost in the middle" effect: rather than burying conclusions
    among long details, a summary of every section's key finding is placed at
    index 0, followed by each detailed section behind an explicit header.

    Args:
        sections: a list of dicts, each with ``title`` (str), ``summary`` (a
            one-line key finding) and ``detail`` (the verbose body).
        summary_header: header used for the synthesized summary section.

    Returns:
        A list of ``{"header", "body"}`` dicts. Element 0 is the summary; each
        following element is one detailed section with its own header.
    """
    summary_lines = [
        f"- {s.get('title', 'Section')}: {s.get('summary', '')}" for s in sections
    ]
    ordered: list[dict[str, str]] = [
        {"header": summary_header, "body": "\n".join(summary_lines)}
    ]
    for s in sections:
        ordered.append(
            {"header": str(s.get("title", "Section")), "body": str(s.get("detail", ""))}
        )
    return ordered


class Scratchpad:
    """A crash-recoverable key/value scratchpad backed by a JSON file.

    Every ``record`` flushes the full state to disk atomically, so findings
    survive a crash and can be read back by a *fresh* ``Scratchpad`` (or a
    different process) pointed at the same path. This counteracts context
    degradation in long sessions: persist key findings, then recall them
    instead of relying on them staying intact in the model's context window.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _flush(self) -> None:
        """Atomically write the current state to ``self.path``."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def record(self, key: str, value: Any) -> None:
        """Record ``value`` under ``key`` and flush to disk immediately."""
        self._data[key] = value
        self._flush()

    def recall(self, key: str, default: Any = None) -> Any:
        """Return the value stored under ``key`` (or ``default`` if absent)."""
        return self._data.get(key, default)


def load_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a structured state manifest (JSON) from ``path``.

    A coordinator resuming after a crash loads the manifest each agent exported
    and re-injects it into agent prompts rather than re-running exploration.

    Args:
        path: filesystem path to a JSON manifest file.

    Returns:
        The parsed manifest as a dict.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))
