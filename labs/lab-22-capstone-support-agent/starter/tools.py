"""Capstone starter — the four MCP-style customer-support tools.

Implement the four Scenario-1 tools with (a) DISAMBIGUATING descriptions in
:data:`TOOLS` (Task Statement 2.1) and (b) STRUCTURED error responses via
:func:`make_error` (Task Statement 2.2). Keep the public API identical to the
reference solution so the shared test suite runs unchanged.

Public API you must provide:
    TOOLS, TOOL_NAMES, CATEGORIES
    make_error(category, message, *, retryable=None) -> dict
    execute_tool(name, tool_input, backends) -> dict
    default_backends() -> dict
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "TOOLS",
    "TOOL_NAMES",
    "CATEGORIES",
    "make_error",
    "execute_tool",
    "default_backends",
]

TOOL_NAMES: tuple[str, ...] = (
    "get_customer",
    "lookup_order",
    "process_refund",
    "escalate_to_human",
)

CATEGORIES: tuple[str, ...] = ("transient", "validation", "business", "permission")

# TODO: replace these minimal descriptions with disambiguating ones that state
# each tool's input format, an example query, edge-case behaviour, and an
# explicit "use this when ... not when ..." boundary pointing at the sibling
# tool (Task Statement 2.1 / Sample Question 2). Also add input_schema per tool.
TOOLS: list[dict[str, Any]] = [
    {"name": "get_customer", "description": "TODO", "input_schema": {"type": "object"}},
    {"name": "lookup_order", "description": "TODO", "input_schema": {"type": "object"}},
    {"name": "process_refund", "description": "TODO", "input_schema": {"type": "object"}},
    {"name": "escalate_to_human", "description": "TODO", "input_schema": {"type": "object"}},
]


def make_error(category: str, message: str, *, retryable: bool | None = None) -> dict[str, Any]:
    """Build ``{"isError", "errorCategory", "isRetryable", "message"}``.

    Only ``transient`` should default to retryable. Raise ``ValueError`` for an
    unknown category or an empty message.
    """
    raise NotImplementedError("Implement make_error (Task Statement 2.2).")


def default_backends() -> dict[str, Any]:
    """Return a fresh set of sample backends (customers, orders) for demos."""
    raise NotImplementedError("Implement default_backends.")


def execute_tool(name: str, tool_input: dict[str, Any], backends: dict[str, Any]) -> dict[str, Any]:
    """Execute one tool call and return its result (success or structured error).

    Honour a per-tool callable override in ``backends`` (so tests can inject a
    transient-then-success sequence), and catch backend exceptions as *transient*
    errors. Distinguish a valid empty result (e.g. no order matched -> found=False)
    from a real access failure (an error object).
    """
    raise NotImplementedError("Implement execute_tool (Task Statements 2.1/2.2/5.3).")
