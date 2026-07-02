"""Extraction with few-shot prompting and a validation-retry loop (Lab 23 — STARTER).

Implement:

* ``build_few_shot_messages()`` — 2-4 examples across varied layouts (narrative,
  tabular, an 'other'/null case, a conflict_detected case) as user/assistant turns.
* ``build_messages(document, *, error_feedback=None, few_shot=True)`` — assemble the
  messages list, optionally prepending few-shot turns and appending error feedback.
* ``extract(client, document, *, tool_choice=None, error_feedback=None, few_shot=True)``
  — one pass; force the extraction tool by default; return the tool_use input dict.
* ``extract_with_retry(client, document, max_retries=2, *, few_shot=True)`` —
  validate, and on a SEMANTIC failure append the error and retry; on info-absent
  (a downstream-required field is null) give up immediately.

Callers inject ``client`` (real SDK or MockAnthropic). Do not construct one here.
"""

from __future__ import annotations

from typing import Any

from schema import (  # noqa: F401  (available for your implementation)
    ValidationError,
    build_extraction_tool,
    format_validation_error,
    missing_required_info,
    validate_extraction,
)

__all__ = [
    "MODEL",
    "MAX_TOKENS",
    "FEW_SHOT_EXAMPLES",
    "build_messages",
    "build_few_shot_messages",
    "extract",
    "extract_with_retry",
]

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1500

# TODO: 2-4 (document, expected extraction) pairs spanning varied layouts.
FEW_SHOT_EXAMPLES: list[dict[str, Any]] = []


def build_few_shot_messages() -> list[dict[str, Any]]:
    """Return few-shot examples as alternating user/assistant turns."""
    raise NotImplementedError("Lab 23: implement build_few_shot_messages")


def build_messages(
    document: str,
    *,
    error_feedback: list[dict[str, Any]] | None = None,
    few_shot: bool = True,
) -> list[dict[str, Any]]:
    """Assemble the messages list for one extraction attempt."""
    raise NotImplementedError("Lab 23: implement build_messages")


def extract(
    client: Any,
    document: str,
    *,
    tool_choice: Any | None = None,
    error_feedback: list[dict[str, Any]] | None = None,
    few_shot: bool = True,
) -> dict[str, Any] | None:
    """Single extraction pass; return the tool_use input dict, or None."""
    raise NotImplementedError("Lab 23: implement extract")


def extract_with_retry(
    client: Any,
    document: str,
    max_retries: int = 2,
    *,
    few_shot: bool = True,
) -> dict[str, Any]:
    """Extract, validate, and retry with error feedback until valid or exhausted."""
    raise NotImplementedError("Lab 23: implement extract_with_retry")
