"""Reference solution for L09 — structured MCP-style error responses.

Exam Task Statement 2.2 ("Implement structured error responses for MCP tools")
and 5.3 ("error propagation across multi-agent systems"). The central idea: a
tool that fails should not return a bare, uniform "Operation failed" string. It
should return STRUCTURED metadata the agent can reason about:

    {"isError": True, "errorCategory": "...", "isRetryable": bool, "message": "..."}

With that metadata the agent (or a coordinator) can decide whether to retry,
communicate a policy limitation to the user, or propagate partial results.

Four error categories are distinguished (guide Task 2.2):
    - transient    timeouts, service unavailability      -> RETRYABLE
    - validation   invalid / malformed input             -> not retryable
    - business     policy violations (e.g. refund > $500) -> not retryable
    - permission   caller not authorized                 -> not retryable

Only *transient* errors are retryable. Returning `isRetryable: false` for the
other three prevents the agent from wasting retry attempts on failures that will
never succeed on their own.

This module is imported by the test suite; it is not a shell script, so the
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

# Only transient failures may be retried. The other three are permanent for a
# given request: retrying identical input will fail the same way.
_RETRYABLE: dict[str, bool] = {
    "transient": True,
    "validation": False,
    "business": False,
    "permission": False,
}

# Keyword hints used by classify() to map free-form kinds / exception text onto a
# category. Order matters: the first category whose keywords match wins, so more
# specific categories (permission, business) are checked before the catch-all.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        "permission",
        (
            "permission", "unauthorized", "forbidden", "not allowed",
            "access denied", "401", "403",
        ),
    ),
    (
        "business",
        (
            "policy", "business rule", "not permitted by policy", "violation",
            "exceeds", "exceed", "threshold", "over the limit", "disallowed",
            "declined",
        ),
    ),
    (
        "validation",
        (
            "invalid", "validation", "malformed", "missing", "required",
            "bad request", "400", "schema", "must be", "not a valid",
        ),
    ),
    (
        "transient",
        (
            "timeout", "timed out", "temporarily", "temporary", "unavailable",
            "connection", "reset", "503", "429", "rate limit", "try again",
            "retry",
        ),
    ),
]


def is_retryable(category: str) -> bool:
    """Return whether errors of ``category`` should be retried.

    Transient errors are retryable; validation, business, and permission errors
    are not. Raises ``ValueError`` for an unknown category.
    """
    if category not in _RETRYABLE:
        raise ValueError(
            f"unknown errorCategory {category!r}; expected one of {CATEGORIES}"
        )
    return _RETRYABLE[category]


def make_error(category: str, message: str, *, retryable: bool | None = None) -> dict[str, Any]:
    """Build an MCP-style structured error object.

    Returns::

        {"isError": True, "errorCategory": category,
         "isRetryable": <bool>, "message": message}

    ``isRetryable`` defaults to ``is_retryable(category)`` but can be overridden
    (e.g. a transient error you have already exhausted retries on). ``category``
    must be one of :data:`CATEGORIES`; ``message`` must be a human-readable,
    non-empty explanation the agent can relay to a user.
    """
    if category not in _RETRYABLE:
        raise ValueError(
            f"unknown errorCategory {category!r}; expected one of {CATEGORIES}"
        )
    if not message or not message.strip():
        raise ValueError("error message must be a non-empty human-readable string")
    resolved = is_retryable(category) if retryable is None else bool(retryable)
    return {
        "isError": True,
        "errorCategory": category,
        "isRetryable": resolved,
        "message": message,
    }


def classify(exc_or_kind: Any) -> str:
    """Map an exception instance or a free-form kind string onto a category.

    Accepts either a Python exception (``TimeoutError``, ``PermissionError``,
    ``ValueError`` …) or a string describing the failure ("timeout", "policy
    violation", "invalid order id"). Always returns one of :data:`CATEGORIES`.

    Recognised exception types take priority; otherwise the class name and text
    are scanned for the keywords in :data:`_KEYWORDS`. An unrecognised failure
    falls back to ``"transient"`` — a bare, uncategorised failure is treated as
    possibly transient, but you should always map known business / validation /
    permission failures explicitly so they are NOT retried.
    """
    if isinstance(exc_or_kind, BaseException):
        # Exact, unambiguous exception types first.
        if isinstance(exc_or_kind, (TimeoutError, ConnectionError)):
            return "transient"
        if isinstance(exc_or_kind, PermissionError):
            return "permission"
        if isinstance(exc_or_kind, (ValueError, KeyError, TypeError)):
            # These usually mean bad input — but let keyword text override
            # (e.g. a ValueError whose message says "policy violation").
            text = f"{type(exc_or_kind).__name__} {exc_or_kind}".lower()
            for category, words in _KEYWORDS:
                if any(w in text for w in words):
                    return category
            return "validation"
        text = f"{type(exc_or_kind).__name__} {exc_or_kind}".lower()
    else:
        kind = str(exc_or_kind).strip().lower()
        # An exact category name passes straight through.
        if kind in _RETRYABLE:
            return kind
        text = kind

    for category, words in _KEYWORDS:
        if any(w in text for w in words):
            return category
    return "transient"


def is_empty_result_vs_failure(result: Any) -> str:
    """Distinguish a successful-but-empty result from an access failure.

    Task Statement 2.2 / 5.3: an agent must NOT confuse "the query succeeded and
    there were no matches" with "the query could not be run". Returns:

    - ``"access_failure"`` — the tool could not complete (an error object, an
      explicit error status, or ``None`` returned in place of a result). The
      coordinator may need to retry or route around it.
    - ``"empty"``          — a successful query that returned zero matches. This
      is a valid answer, not an error; do not retry it.
    - ``"results"``        — a successful query that returned one or more matches.

    Silently returning empty results as success (hiding a real failure) is the
    anti-pattern this check exists to prevent.
    """
    # None is not a valid result payload — treat it as a failure to surface.
    if result is None:
        return "access_failure"

    if isinstance(result, dict):
        if result.get("isError") is True:
            return "access_failure"
        if result.get("ok") is False:
            return "access_failure"
        status = str(result.get("status", "")).lower()
        if status in {"error", "failed", "failure", "unavailable", "timeout"}:
            return "access_failure"
        if result.get("error"):
            return "access_failure"

        # Successful dict: find the collection it carries.
        for key in ("results", "matches", "items", "data", "records", "rows", "hits"):
            if key in result and isinstance(result[key], (list, tuple, str)):
                return "empty" if len(result[key]) == 0 else "results"
        if "count" in result and isinstance(result["count"], int):
            return "empty" if result["count"] == 0 else "results"
        # A payload dict with no recognised collection: empty {} vs populated.
        return "empty" if len(result) == 0 else "results"

    if isinstance(result, (list, tuple, str)):
        return "empty" if len(result) == 0 else "results"

    # Any other scalar: truthy means a real value came back.
    return "results" if result else "empty"
