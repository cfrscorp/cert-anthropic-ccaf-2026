"""Validation, retry, and feedback loops for extraction (Lab 10 reference).

Task Statement 4.4 in three moves:

1. **Extract → validate.** Call Claude (via an injected client) to fill an
   extraction tool, then run the result through the Pydantic model in
   ``models.py``. Tool use removes syntax errors; the model catches semantics.

2. **Retry WITH error feedback.** On a validation failure, append the *specific*
   validation error text — plus the failed extraction and the original document —
   to the next request so the model can self-correct. Generic "try again"
   prompts do not help; the specific error does.

3. **Know when to stop.** Retries only help for *format* and *structural*
   errors. When the information is simply absent from the source, or the source
   is internally inconsistent (a real conflict), retrying just burns tokens.
   ``should_retry`` / ``is_retryable_error`` encode that decision so the loop
   gives up instead of looping pointlessly.

Public API (identical in starter/ and solution/):

    extract_with_retry(client, document, *, max_retries=2) -> dict
    is_retryable_error(kind: str) -> bool
    should_retry(document, error) -> bool
    classify_error(error, document="") -> str          # helper, also public

The client is injected (real SDK or MockAnthropic) so tests run offline.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from models import InvoiceExtraction

__all__ = [
    "extract_with_retry",
    "is_retryable_error",
    "should_retry",
    "classify_error",
    "build_extraction_tool",
    "MODEL",
]

MODEL = "claude-sonnet-5"

# --------------------------------------------------------------------------- #
# Error-kind taxonomy                                                          #
# --------------------------------------------------------------------------- #
# Retries help for format/structural problems (the info is there, the model
# just shaped it wrong) but NOT for info-absent or genuine source conflicts.
_RETRYABILITY: dict[str, bool] = {
    "format": True,       # wrong date format, currency casing, wrong field placement
    "structural": True,   # required field omitted, but the info IS in the document
    "info_absent": False,  # required info simply is not in the source document
    "source_conflict": False,  # source contradicts itself (totals/dates don't reconcile)
}

# Words that would appear in a document IF a given field's info were present.
# Used to distinguish "the model dropped a field that is there" (structural,
# retryable) from "the info genuinely is not in the document" (info_absent).
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

    Retryable: ``"format"``, ``"structural"``.
    Not retryable: ``"info_absent"``, ``"source_conflict"``.

    Raises:
        ValueError: for an unknown kind.
    """
    try:
        return _RETRYABILITY[kind]
    except KeyError:
        raise ValueError(
            f"Unknown error kind {kind!r}; expected one of {sorted(_RETRYABILITY)}"
        ) from None


# --------------------------------------------------------------------------- #
# Error classification                                                         #
# --------------------------------------------------------------------------- #
def _error_dicts(error: Any) -> list[dict[str, Any]]:
    """Normalize whatever we're handed into a list of Pydantic-style error dicts."""
    if isinstance(error, ValidationError):
        return error.errors()
    if isinstance(error, dict):
        return [error]
    if isinstance(error, list):
        return list(error)
    return [{"type": "value_error", "loc": (), "msg": str(error)}]


def _field_of(err: dict[str, Any]) -> str | None:
    loc = err.get("loc") or ()
    return str(loc[0]) if loc else None


def _classify_single(err: dict[str, Any], document: str) -> str:
    """Classify one Pydantic error dict into a retry kind."""
    etype = str(err.get("type", ""))
    msg = str(err.get("msg", "")).lower()

    # Our semantic validator embeds the pattern name in the message.
    if "mismatch" in msg or "contradict" in msg or "detected_pattern" in msg:
        return "source_conflict"

    # A required field is missing: is the info in the document at all?
    if etype == "missing":
        field = _field_of(err)
        hints = FIELD_HINTS.get(field or "", ())
        doc = document.lower()
        if hints and not any(h in doc for h in hints):
            return "info_absent"   # not in the source; a retry cannot invent it
        return "structural"        # the info is there; the model just dropped it

    # Everything else (bad date string, wrong type, bad length) is a format issue.
    return "format"


def classify_error(error: Any, document: str = "") -> str:
    """Return the single most *blocking* kind across all errors in ``error``.

    Non-retryable kinds win: if any sub-error is ``info_absent`` or
    ``source_conflict`` the whole failure is treated that way, because retrying
    cannot fix it regardless of the other errors.
    """
    kinds = [_classify_single(e, document) for e in _error_dicts(error)]
    for kind in ("source_conflict", "info_absent"):
        if kind in kinds:
            return kind
    if "structural" in kinds:
        return "structural"
    return "format"


def should_retry(document: str, error: Any) -> bool:
    """Decide whether re-asking the model could plausibly fix ``error``.

    Returns ``False`` as soon as any sub-error is non-retryable (info absent from
    the source, or a genuine source conflict) — those never improve on retry.
    """
    for err in _error_dicts(error):
        if not is_retryable_error(_classify_single(err, document)):
            return False
    return True


# --------------------------------------------------------------------------- #
# Extraction tool + request building                                          #
# --------------------------------------------------------------------------- #
_TOOL_NAME = "record_invoice"


def build_extraction_tool() -> dict[str, Any]:
    """A tool whose input_schema is the extraction schema (removes syntax errors)."""
    return {
        "name": _TOOL_NAME,
        "description": (
            "Record the invoice fields extracted from the document. Copy values "
            "verbatim; use ISO 8601 (YYYY-MM-DD) for dates and a 3-letter ISO "
            "4217 code for currency. Never invent values not present in the "
            "document."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string"},
                "invoice_number": {"type": "string"},
                "invoice_date": {"type": "string"},
                "due_date": {"type": ["string", "null"]},
                "currency": {"type": "string"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "amount": {"type": "number"},
                        },
                        "required": ["description", "amount"],
                    },
                },
                "stated_total": {"type": "number"},
            },
            "required": [
                "vendor_name",
                "invoice_number",
                "invoice_date",
                "currency",
                "line_items",
                "stated_total",
            ],
        },
    }


def _format_feedback(error: ValidationError) -> str:
    """Turn validation errors into a specific, model-actionable bullet list."""
    lines = []
    for err in error.errors():
        loc = ".".join(str(p) for p in (err.get("loc") or ())) or "(root)"
        lines.append(f"- {loc}: {err.get('msg', '')}")
    return "\n".join(lines)


def _build_messages(
    document: str, feedback: str | None, prior: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """First request is plain; a retry appends the failed extraction + errors."""
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Extract the invoice by calling {_TOOL_NAME}.\n\n"
                f"<document>\n{document}\n</document>"
            ),
        }
    ]
    if feedback is not None:
        # Include the ORIGINAL document (above), the FAILED extraction, and the
        # SPECIFIC validation errors — the three ingredients for self-correction.
        messages.append(
            {
                "role": "assistant",
                "content": f"Previous extraction attempt:\n{json.dumps(prior)}",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "That extraction FAILED validation with these specific "
                    f"errors:\n{feedback}\n\n"
                    "Fix only these problems and call the tool again. Do not "
                    "change fields that were already correct."
                ),
            }
        )
    return messages


def _tool_input(resp: Any) -> dict[str, Any]:
    """Pull the tool_use block's input out of a mock/real response."""
    for block in getattr(resp, "content", []):
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    return {}


# --------------------------------------------------------------------------- #
# The retry loop                                                              #
# --------------------------------------------------------------------------- #
def extract_with_retry(
    client: Any,
    document: str,
    *,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Extract, validate, and retry with specific error feedback.

    Args:
        client: an Anthropic-style client (real or MockAnthropic).
        document: the raw document text.
        max_retries: extra attempts AFTER the first (so up to
            ``max_retries + 1`` model calls).

    Returns:
        ``{"data": ..., "attempts": int, "succeeded": bool}`` plus, on failure,
        ``"error"`` (the specific validation messages) and ``"detected_pattern"``.
        ``data`` is the validated, serialized invoice on success, or the last raw
        extraction on failure.
    """
    tool = build_extraction_tool()
    feedback: str | None = None
    prior: dict[str, Any] | None = None
    attempts = 0
    last_error: ValidationError | None = None
    last_raw: dict[str, Any] = {}

    while attempts <= max_retries:
        attempts += 1
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=_build_messages(document, feedback, prior),
        )
        raw = _tool_input(resp)
        last_raw = raw

        try:
            invoice = InvoiceExtraction.model_validate(raw)
        except ValidationError as exc:
            last_error = exc
            # Give up early if retrying cannot possibly help.
            if not should_retry(document, exc):
                return {
                    "data": raw,
                    "attempts": attempts,
                    "succeeded": False,
                    "error": _format_feedback(exc),
                    "detected_pattern": _pattern_from(exc),
                }
            # Otherwise loop again with the SPECIFIC errors appended as feedback.
            feedback = _format_feedback(exc)
            prior = raw
            continue

        return {
            "data": invoice.model_dump(mode="json"),
            "attempts": attempts,
            "succeeded": True,
        }

    # Retries exhausted while errors were still (in principle) retryable.
    return {
        "data": last_raw,
        "attempts": attempts,
        "succeeded": False,
        "error": _format_feedback(last_error) if last_error else "",
        "detected_pattern": _pattern_from(last_error) if last_error else None,
    }


def _pattern_from(error: ValidationError | None) -> str | None:
    """Surface the detected_pattern label embedded in a semantic error message."""
    if error is None:
        return None
    for err in error.errors():
        msg = str(err.get("msg", ""))
        marker = "detected_pattern="
        if marker in msg:
            return msg.split(marker, 1)[1].rstrip("].)").strip()
    return None
