"""Extraction with few-shot prompting and a validation-retry loop (Lab 23 — SOLUTION).

Public API (identical in starter/ and solution/):

    build_messages(document, *, error_feedback=None, few_shot=True) -> list[dict]
    build_few_shot_messages() -> list[dict]
    extract(client, document, *, tool_choice=None, error_feedback=None, few_shot=True) -> dict | None
    extract_with_retry(client, document, max_retries=2, *, few_shot=True) -> dict

This is the integrative core of the capstone. It combines:

* **Structured output via tool_use** (4.3) — force the extraction tool so the reply
  is guaranteed schema-shaped JSON we read straight from the tool_use block.
* **Few-shot examples** (4.2) — prior turns demonstrate correct extraction from a
  narrative invoice, a tabular receipt, an "other"/null case, and a genuinely
  inconsistent document (conflict_detected=true). This teaches the model to
  generalise across document formats instead of matching one layout.
* **Validation + retry with error feedback** (4.4) — validate with Pydantic; on a
  semantic failure append the failed extraction and the specific error and try
  again. Crucially, recognise when a retry is *futile*: if a downstream-required
  field came back null the information is simply absent from the source, so give up
  immediately (route to human) rather than burning retries.

Callers inject the Anthropic client (real SDK or MockAnthropic) so tests run
offline. Do not construct a client inside these functions.
"""

from __future__ import annotations

import json
from typing import Any

from schema import (
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

# Format-normalisation guidance travels WITH the strict schema (4.3): the schema
# guarantees shape, the prompt guarantees how varied source formatting is mapped in.
_SYSTEM_HINT = (
    "Normalise while extracting: strip currency symbols and thousands separators "
    "from amounts, convert dates to ISO 8601 (YYYY-MM-DD), and copy identifiers "
    "verbatim. Return null for anything the document does not state."
)

# Few-shot examples span deliberately different layouts so the model generalises
# (4.2). Each is a (document, expected extraction) pair. The "other"/null example
# shows the enum escape hatch and null pass-through; the last shows a genuinely
# inconsistent source flagged with conflict_detected=true rather than reconciled.
FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "document": (
            "NORTHWIND TRADING — Invoice INV-2207 dated 2026-03-01, net 30. "
            "One line: Consulting, 10 hrs @ $150 = $1,500.00. Total due USD 1,500.00 "
            "by 2026-03-31."
        ),
        "extraction": {
            "vendor_name": "Northwind Trading",
            "invoice_number": "INV-2207",
            "document_type": "invoice",
            "currency": "USD",
            "conflict_detected": False,
            "stated_total": 1500.00,
            "due_date": "2026-03-31",
            "document_type_detail": None,
            "purchase_order_number": None,
            "line_items": [
                {"description": "Consulting", "quantity": 10, "unit_price": 150, "amount": 1500.00}
            ],
        },
    },
    {
        "document": (
            "QuickMart POS receipt #55-9910\nMilk 2 x 1.99 ... 3.98\nBread ... 2.50\n"
            "TOTAL  6.48 USD  (cash)"
        ),
        "extraction": {
            "vendor_name": "QuickMart",
            "invoice_number": "55-9910",
            "document_type": "receipt",
            "currency": "USD",
            "conflict_detected": False,
            "stated_total": 6.48,
            "due_date": None,
            "document_type_detail": None,
            "purchase_order_number": None,
            "line_items": [
                {"description": "Milk", "quantity": 2, "unit_price": 1.99, "amount": 3.98},
                {"description": "Bread", "quantity": 1, "unit_price": 2.50, "amount": 2.50},
            ],
        },
    },
    {
        "document": (
            "MEMBERSHIP STATEMENT — Cascade Climbing Co-op. Member dues confirmation "
            "MS-0042. Amount recorded: EUR 240.00. No payment due date listed."
        ),
        "extraction": {
            "vendor_name": "Cascade Climbing Co-op",
            "invoice_number": "MS-0042",
            "document_type": "other",
            "currency": "EUR",
            "conflict_detected": False,
            "stated_total": 240.00,
            "due_date": None,
            "document_type_detail": "membership dues statement",
            "purchase_order_number": None,
            "line_items": None,
        },
    },
    {
        "document": (
            "Invoice AC-88 from Acme. Lines: Widget 40.00, Gasket 35.00. "
            "Printed TOTAL: 100.00 USD. (The printed total does not match the lines.)"
        ),
        "extraction": {
            "vendor_name": "Acme",
            "invoice_number": "AC-88",
            "document_type": "invoice",
            "currency": "USD",
            "conflict_detected": True,
            "stated_total": 100.00,
            "due_date": None,
            "document_type_detail": None,
            "purchase_order_number": None,
            "line_items": [
                {"description": "Widget", "quantity": 1, "unit_price": 40.00, "amount": 40.00},
                {"description": "Gasket", "quantity": 1, "unit_price": 35.00, "amount": 35.00},
            ],
        },
    },
]


def _extraction_prompt(document: str) -> str:
    return (
        f"{_SYSTEM_HINT}\n\n"
        "Extract the billing data from the following document by calling the "
        "extract_invoice tool.\n\n"
        f"<document>\n{document}\n</document>"
    )


def _feedback_prompt(failed: dict[str, Any] | None, error: str) -> str:
    failed_json = json.dumps(failed, indent=2, sort_keys=True) if failed is not None else "(no tool call)"
    return (
        "Your previous extraction was rejected by validation.\n\n"
        f"<previous_extraction>\n{failed_json}\n</previous_extraction>\n\n"
        f"<validation_errors>\n{error}\n</validation_errors>\n\n"
        "Re-extract from the SAME document, fixing exactly these problems. "
        "Do not fabricate values — return null for anything the document does not "
        "state."
    )


def build_few_shot_messages() -> list[dict[str, Any]]:
    """Return few-shot examples as alternating user/assistant turns.

    Each example is shown as a user document followed by the assistant's correct
    extraction (rendered as JSON text). This demonstrates the target format and
    the handling of varied layouts, nulls, the 'other' enum, and flagged conflicts.
    """
    msgs: list[dict[str, Any]] = []
    for ex in FEW_SHOT_EXAMPLES:
        msgs.append(
            {
                "role": "user",
                "content": f"Example document:\n<document>\n{ex['document']}\n</document>",
            }
        )
        msgs.append(
            {
                "role": "assistant",
                "content": (
                    "Correct extraction:\n"
                    + json.dumps(ex["extraction"], indent=2, sort_keys=True)
                ),
            }
        )
    return msgs


def build_messages(
    document: str,
    *,
    error_feedback: list[dict[str, Any]] | None = None,
    few_shot: bool = True,
) -> list[dict[str, Any]]:
    """Assemble the messages list for one extraction attempt.

    Args:
        document: the raw document text.
        error_feedback: prior failed attempts, each ``{"failed": dict, "error": str}``.
            Appended as extra user turns so the model self-corrects (4.4).
        few_shot: prepend the few-shot demonstration turns (4.2).
    """
    msgs: list[dict[str, Any]] = []
    if few_shot:
        msgs.extend(build_few_shot_messages())
    msgs.append({"role": "user", "content": _extraction_prompt(document)})
    for fb in error_feedback or []:
        msgs.append(
            {"role": "user", "content": _feedback_prompt(fb.get("failed"), fb.get("error", ""))}
        )
    return msgs


def _read_tool_use(resp: Any, tool_name: str) -> dict[str, Any] | None:
    blocks = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
    for block in blocks:
        if block.name == tool_name:
            return dict(block.input)
    if blocks:
        return dict(blocks[0].input)
    return None


def extract(
    client: Any,
    document: str,
    *,
    tool_choice: Any | None = None,
    error_feedback: list[dict[str, Any]] | None = None,
    few_shot: bool = True,
) -> dict[str, Any] | None:
    """Single extraction pass. Returns the tool_use input dict, or None.

    Defaults to forcing the extraction tool so the reply is guaranteed structured
    output rather than free text. ``error_feedback`` appends prior-attempt errors
    for self-correction; ``few_shot`` toggles the demonstration turns.
    """
    tool = build_extraction_tool()
    if tool_choice is None:
        tool_choice = {"type": "tool", "name": tool["name"]}

    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[tool],
        tool_choice=tool_choice,
        messages=build_messages(document, error_feedback=error_feedback, few_shot=few_shot),
    )
    return _read_tool_use(resp, tool["name"])


def extract_with_retry(
    client: Any,
    document: str,
    max_retries: int = 2,
    *,
    few_shot: bool = True,
) -> dict[str, Any]:
    """Extract, validate, and retry with error feedback until valid or exhausted.

    Returns a result dict::

        {
          "status": "ok" | "gave_up",
          "reason": None | "info_absent" | "validation_failed" | "no_tool_call",
          "extraction": <last raw dict or None>,
          "invoice": <Invoice on success, else None>,
          "attempts": <int, API calls made>,
          "errors": [<feedback strings>],
          "missing_fields": [<downstream-required nulls, if info_absent>],
        }

    Retry policy (Task Statement 4.4):
      * Semantic failure (e.g. line items don't sum) -> append the error and retry;
        these are usually transcription mistakes a follow-up can fix.
      * Downstream-required field is null -> the information is ABSENT from the
        source. Retrying the same document cannot help, so give up immediately and
        surface the missing fields for human/upstream handling.
    """
    feedback: list[dict[str, Any]] = []
    errors: list[str] = []
    attempts = 0
    last: dict[str, Any] | None = None

    for _ in range(max_retries + 1):
        attempts += 1
        data = extract(client, document, error_feedback=feedback or None, few_shot=few_shot)
        last = data

        if data is None:
            msg = "model returned no tool call; you must call extract_invoice"
            errors.append(msg)
            feedback.append({"failed": None, "error": msg})
            continue

        # Futile-retry detection: absent info can't be recovered by retrying.
        missing = missing_required_info(data)
        if missing:
            return {
                "status": "gave_up",
                "reason": "info_absent",
                "extraction": data,
                "invoice": None,
                "attempts": attempts,
                "errors": errors,
                "missing_fields": missing,
            }

        try:
            invoice = validate_extraction(data)
        except ValidationError as exc:
            msg = format_validation_error(exc)
            errors.append(msg)
            feedback.append({"failed": data, "error": msg})
            continue

        return {
            "status": "ok",
            "reason": None,
            "extraction": data,
            "invoice": invoice,
            "attempts": attempts,
            "errors": errors,
            "missing_fields": [],
        }

    return {
        "status": "gave_up",
        "reason": "validation_failed",
        "extraction": last,
        "invoice": None,
        "attempts": attempts,
        "errors": errors,
        "missing_fields": [],
    }
