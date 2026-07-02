"""Starter scaffold: structured MCP-style error responses (Task Statement 2.2).

Implement the four functions below so a failing tool returns STRUCTURED error
metadata instead of a bare "Operation failed" string. The required shape is:

    {"isError": True, "errorCategory": "...", "isRetryable": bool, "message": "..."}

Four categories (guide Task 2.2):
    transient   -> timeouts / service unavailable -> RETRYABLE
    validation  -> invalid input                  -> not retryable
    business    -> policy violations              -> not retryable
    permission  -> caller not authorized          -> not retryable

Only transient errors are retryable. See README.md for the full spec.

This module is imported by the test suite (not run from a shell), so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "CATEGORIES",
    "make_error",
    "is_retryable",
    "classify",
    "is_empty_result_vs_failure",
]

# The four categories from Task Statement 2.2.
CATEGORIES: tuple[str, ...] = ("transient", "validation", "business", "permission")


def is_retryable(category: str) -> bool:
    """Return whether errors of ``category`` should be retried.

    Transient errors are retryable; validation, business, and permission errors
    are not. Raise ``ValueError`` for an unknown category.
    """
    # TODO: return True only for "transient"; False for validation/business/
    #       permission; raise ValueError for anything else.
    raise NotImplementedError("Implement is_retryable (see README.md).")


def make_error(category: str, message: str, *, retryable: bool | None = None) -> dict[str, Any]:
    """Build an MCP-style structured error object.

    Return {"isError": True, "errorCategory": category, "isRetryable": <bool>,
    "message": message}. ``isRetryable`` defaults to ``is_retryable(category)``
    unless ``retryable`` is given. Validate ``category`` and require a non-empty
    ``message``.
    """
    # TODO: validate category and message; resolve isRetryable; return the dict.
    raise NotImplementedError("Implement make_error (see README.md).")


def classify(exc_or_kind: Any) -> str:
    """Map an exception instance or a kind string onto one of CATEGORIES.

    Accept a Python exception (TimeoutError, PermissionError, ValueError, …) or a
    string ("timeout", "policy violation", "invalid id"). Always return one of
    CATEGORIES.
    """
    # TODO: map known exception types (TimeoutError/ConnectionError -> transient,
    #       PermissionError -> permission, ValueError/KeyError/TypeError ->
    #       validation) and/or scan the text for category keywords.
    raise NotImplementedError("Implement classify (see README.md).")


def is_empty_result_vs_failure(result: Any) -> str:
    """Distinguish a successful-but-empty result from an access failure.

    Return "access_failure" for an error object / error status / None; "empty"
    for a successful query with zero matches; "results" for one or more matches.
    """
    # TODO: an error dict (isError True), an error status, or None -> "access_failure";
    #       a successful result whose collection is empty -> "empty"; otherwise "results".
    raise NotImplementedError("Implement is_empty_result_vs_failure (see README.md).")
