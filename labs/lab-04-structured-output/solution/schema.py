"""Extraction tool definition for Lab 04 (reference solution).

The core idea of Task Statement 4.3: the tool's ``input_schema`` *is* the output
schema. When Claude is asked to call this tool, the JSON it produces for the
tool's input is guaranteed to be syntactically valid and schema-shaped. We then
read the structured data straight out of the ``tool_use`` block.

Schema design choices demonstrated here:

* **required vs optional** — ``required`` lists the fields that must always be
  present. Fields left out of ``required`` (``purchase_order_number``,
  ``line_items``) are optional: the model may omit them entirely.
* **nullable fields** — ``due_date`` and ``document_type_detail`` are *required*
  but their ``type`` allows ``"null"`` (``["string", "null"]``). This forces the
  model to consider them on every document yet lets it answer ``null`` when the
  information is genuinely absent, instead of fabricating a value to satisfy a
  non-null required field.
* **enum with "other" + detail** — ``document_type`` is a closed enum, but it
  includes an ``"other"`` escape hatch paired with the free-text
  ``document_type_detail`` so the category set stays extensible without a schema
  change.

Remember: a strict schema removes *syntax* errors (malformed JSON, missing keys,
wrong types) but NOT *semantic* errors. Nothing here guarantees the
``line_items`` amounts actually sum to ``total_amount`` — that is a semantic
check you must perform after extraction (see Task Statement 4.4).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "TOOL_NAME",
    "TOOL_DESCRIPTION",
    "DOCUMENT_TYPES",
    "INPUT_SCHEMA",
    "EXTRACTION_TOOL",
]

TOOL_NAME = "extract_invoice"

TOOL_DESCRIPTION = (
    "Extract structured billing data from an unstructured invoice or receipt. "
    "Call this tool with exactly one argument object matching the input schema. "
    "Copy values verbatim from the document. If a field's information is not "
    "present in the document, return null for that field rather than guessing or "
    "inferring a value. Do not compute or reconcile totals; report the stated "
    "values as-is."
)

# Closed category set with an "other" escape hatch (see document_type_detail).
DOCUMENT_TYPES = ["invoice", "receipt", "purchase_order", "credit_note", "other"]

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        # --- required, non-null ------------------------------------------- #
        "vendor_name": {
            "type": "string",
            "description": "Legal or trading name of the party issuing the document.",
        },
        "invoice_number": {
            "type": "string",
            "description": "The document's own identifier (invoice #, receipt #).",
        },
        "document_type": {
            "type": "string",
            "enum": DOCUMENT_TYPES,
            "description": (
                "The kind of document. Use 'other' only when none of the named "
                "categories fit, and then fill document_type_detail."
            ),
        },
        "total_amount": {
            "type": "number",
            "description": "The grand total stated on the document (numeric, no currency symbol).",
        },
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code of total_amount, e.g. 'USD'.",
        },
        # --- required, but nullable (model must answer, null if absent) ---- #
        "due_date": {
            "type": ["string", "null"],
            "description": (
                "Payment due date in ISO 8601 (YYYY-MM-DD), or null if the "
                "document states no due date. Do not invent a date."
            ),
        },
        "document_type_detail": {
            "type": ["string", "null"],
            "description": (
                "Free-text label describing the document when document_type is "
                "'other'; null for every other document_type."
            ),
        },
        # --- optional (may be omitted entirely) --------------------------- #
        "purchase_order_number": {
            "type": ["string", "null"],
            "description": "Referenced PO number if present, else null.",
        },
        "line_items": {
            "type": "array",
            "description": "Individual billed lines, if the document itemizes them.",
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
    },
    # Optional fields (purchase_order_number, line_items) are deliberately NOT
    # listed here. Nullable fields ARE required so the model always addresses
    # them — returning null rather than omitting or fabricating.
    "required": [
        "vendor_name",
        "invoice_number",
        "document_type",
        "total_amount",
        "currency",
        "due_date",
        "document_type_detail",
    ],
}

# The full tool definition passed to client.messages.create(tools=[...]).
EXTRACTION_TOOL: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "input_schema": INPUT_SCHEMA,
}
