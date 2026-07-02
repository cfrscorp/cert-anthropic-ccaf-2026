"""Validation, retry, and feedback loops for extraction (Lab 10 STARTER).

Implement Task Statement 4.4:

  1. Extract (call the injected client to fill the extraction tool), then
     validate with ``InvoiceExtraction`` from ``models.py``.
  2. On a validation failure, append the SPECIFIC error messages (plus the failed
     extraction and original document) to the next request and retry.
  3. Stop early when retrying cannot help: info absent from the source, or a
     genuine source conflict. Use ``should_retry`` / ``is_retryable_error``.

Public API (must match solution/):

    extract_with_retry(client, document, *, max_retries=2) -> dict
    is_retryable_error(kind: str) -> bool
    should_retry(document, error) -> bool
    classify_error(error, document="") -> str

The client is injected (real SDK or MockAnthropic) so tests run offline.
"""

from __future__ import annotations

import json  # noqa: F401  (useful when building retry feedback messages)
from typing import Any

from pydantic import ValidationError  # noqa: F401

from models import InvoiceExtraction  # noqa: F401

__all__ = [
    "extract_with_retry",
    "is_retryable_error",
    "should_retry",
    "classify_error",
    "build_extraction_tool",
    "MODEL",
]

MODEL = "claude-sonnet-5"

# Retryable: "format", "structural". Not retryable: "info_absent",
# "source_conflict". (Fill this in and use it from is_retryable_error.)
_RETRYABILITY: dict[str, bool] = {
    "format": True,
    "structural": True,
    "info_absent": False,
    "source_conflict": False,
}

# Words that would appear in a document IF a field's info were present. Use these
# to tell "model dropped a field that IS there" (structural) from "the info is
# genuinely absent" (info_absent).
FIELD_HINTS: dict[str, tuple[str, ...]] = {
    "invoice_number": ("invoice #", "invoice no", "invoice number", "inv-", "invoice:"),
    "vendor_name": ("from", "vendor", "issued by", "bill from", "seller"),
    "invoice_date": ("date",),
    "due_date": ("due", "net "),
    "currency": ("usd", "eur", "gbp", "cad", "aud", "$", "€", "£"),
    "stated_total": ("total", "amount due", "balance due", "grand total"),
}


def is_retryable_error(kind: str) -> bool:
    """Return whether an error of ``kind`` is worth retrying.

    Retryable: "format", "structural". Not retryable: "info_absent",
    "source_conflict". Raise ``ValueError`` for an unknown kind.
    """
    # TODO: implement using _RETRYABILITY; raise ValueError for unknown kinds.
    raise NotImplementedError("is_retryable_error: map kind -> bool")


def classify_error(error: Any, document: str = "") -> str:
    """Return the most *blocking* error kind across all sub-errors.

    Hints:
      * A message mentioning a mismatch/contradiction -> "source_conflict".
      * A Pydantic "missing" error -> "info_absent" if no FIELD_HINTS word for
        that field appears in ``document``, else "structural".
      * Anything else -> "format".
      * Non-retryable kinds win over retryable ones.
    """
    # TODO: implement per the docstring.
    raise NotImplementedError("classify_error: classify a ValidationError into a kind")


def should_retry(document: str, error: Any) -> bool:
    """Return True only if re-asking the model could plausibly fix ``error``.

    Return False as soon as any sub-error is non-retryable.
    """
    # TODO: implement using classify/ is_retryable_error over each sub-error.
    raise NotImplementedError("should_retry: decide whether a retry can help")


def build_extraction_tool() -> dict[str, Any]:
    """Return a tool whose input_schema is the invoice extraction schema."""
    # TODO: return a tool dict (name/description/input_schema) for the extraction.
    raise NotImplementedError("build_extraction_tool: return the extraction tool dict")


def extract_with_retry(
    client: Any,
    document: str,
    *,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Extract, validate, and retry with SPECIFIC error feedback.

    Steps:
      1. Call ``client.messages.create(...)`` forcing the extraction tool; read
         the tool_use block's input.
      2. Validate it with ``InvoiceExtraction.model_validate``.
      3. On success: return
         ``{"data": invoice.model_dump(mode="json"), "attempts": n, "succeeded": True}``.
      4. On ``ValidationError``: if ``should_retry`` is False, stop and return
         ``succeeded=False``. Otherwise append the specific errors (and the failed
         extraction + original document) to the next request and loop.
      5. ``max_retries`` is the number of retries AFTER the first attempt.
    """
    # TODO: implement the extract -> validate -> retry-with-feedback loop.
    raise NotImplementedError("extract_with_retry: implement the validate/retry loop")
