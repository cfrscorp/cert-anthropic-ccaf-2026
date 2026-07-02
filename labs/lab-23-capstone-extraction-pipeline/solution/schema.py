"""Extraction schema + semantic validation (Lab 23 capstone — SOLUTION).

This module carries the *contract* the whole pipeline is built around. Two layers
work together and it is important to keep them distinct:

1. **Structural layer — the tool input_schema** (Task Statement 4.3).
   The extraction tool's ``input_schema`` *is* the output schema. Asking Claude to
   call this tool guarantees syntactically valid, schema-shaped JSON. Schema design
   choices demonstrated here:

   * **required vs optional** — ``required`` lists fields that must always appear.
     Fields left out (``purchase_order_number``, ``line_items``) may be omitted.
   * **nullable required fields** — ``stated_total``, ``due_date`` and
     ``document_type_detail`` are *required* but their type allows ``"null"``. The
     model must address them on every document, yet may answer ``null`` when the
     information is genuinely absent instead of fabricating a value to satisfy a
     non-null required field.
   * **enum with "other" + detail** — ``document_type`` is a closed enum with an
     ``"other"`` escape hatch paired with the free-text ``document_type_detail`` so
     the category set stays extensible without a schema change.

2. **Semantic layer — the Pydantic model** (Task Statement 4.4).
   A strict JSON schema removes *syntax* errors but NOT *semantic* ones: nothing in
   the schema forces ``line_items`` to sum to ``stated_total`` or values to land in
   the right field. :class:`Invoice` runs those checks after extraction:

   * ``calculated_total`` is derived from the line items and compared to the
     model-reported ``stated_total``.
   * A mismatch normally raises — this is a *retryable* error (the model probably
     mis-transcribed an amount; feeding the error back can fix it).
   * ...unless the model set ``conflict_detected=True``, meaning the *source itself*
     is internally inconsistent. That is not a transcription bug to retry away; it
     is real, so we keep the extraction and route it to a human instead.

Also provided: :func:`missing_required_info`, which detects when a field required by
downstream systems is null. That is the *info-absent* signal — no amount of retrying
will conjure a total the document never stated (Task Statement 4.4).
"""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ValidationError, model_validator

__all__ = [
    "TOOL_NAME",
    "TOOL_DESCRIPTION",
    "DOCUMENT_TYPES",
    "INPUT_SCHEMA",
    "EXTRACTION_TOOL",
    "REQUIRED_DOWNSTREAM",
    "TOLERANCE",
    "LineItem",
    "Invoice",
    "build_extraction_tool",
    "validate_extraction",
    "missing_required_info",
    "format_validation_error",
    "ValidationError",
]

TOOL_NAME = "extract_invoice"

TOOL_DESCRIPTION = (
    "Extract structured billing data from an unstructured invoice, receipt, "
    "purchase order, or credit note. Call this tool with exactly one argument "
    "object matching the input schema. Copy values verbatim from the document. "
    "If a field's information is not present in the document, return null for that "
    "field rather than guessing. Set conflict_detected=true ONLY when the document "
    "itself is internally inconsistent (e.g. the printed line items genuinely do "
    "not add up to the printed total). Do not silently reconcile such conflicts."
)

# Closed category set with an "other" escape hatch (see document_type_detail).
DOCUMENT_TYPES = ["invoice", "receipt", "purchase_order", "credit_note", "other"]

# Fields downstream systems cannot work without. A null in any of these is the
# "information absent from source" signal that makes a retry futile.
REQUIRED_DOWNSTREAM = ["vendor_name", "invoice_number", "currency", "stated_total"]

# Currency rounding tolerance when reconciling line items against the total.
TOLERANCE = 0.01

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
            "description": "The document's own identifier (invoice #, receipt #, PO #).",
        },
        "document_type": {
            "type": "string",
            "enum": DOCUMENT_TYPES,
            "description": (
                "The kind of document. Use 'other' only when none of the named "
                "categories fit, and then fill document_type_detail."
            ),
        },
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code of the amounts, e.g. 'USD'.",
        },
        "conflict_detected": {
            "type": "boolean",
            "description": (
                "True only when the document is internally inconsistent (line items "
                "do not add up to the stated total AS PRINTED). False otherwise."
            ),
        },
        # --- required, but nullable (model must answer, null if absent) ---- #
        "stated_total": {
            "type": ["number", "null"],
            "description": (
                "The grand total printed on the document (numeric, no currency "
                "symbol), or null if the document states no total. Do not compute "
                "it from the line items; report the printed value as-is."
            ),
        },
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
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "amount": {"type": "number"},
                },
                "required": ["description", "amount"],
            },
        },
    },
    # Optional fields (purchase_order_number, line_items) are deliberately NOT
    # listed. Nullable fields ARE required so the model always addresses them —
    # returning null rather than omitting or fabricating.
    "required": [
        "vendor_name",
        "invoice_number",
        "document_type",
        "currency",
        "conflict_detected",
        "stated_total",
        "due_date",
        "document_type_detail",
    ],
}

EXTRACTION_TOOL: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "input_schema": INPUT_SCHEMA,
}


def build_extraction_tool() -> dict[str, Any]:
    """Return a fresh deep copy of the extraction tool definition.

    A copy is returned so callers/tests can mutate the result without corrupting
    the shared schema module.
    """
    return copy.deepcopy(EXTRACTION_TOOL)


# --------------------------------------------------------------------------- #
# Semantic layer                                                              #
# --------------------------------------------------------------------------- #
class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float


class Invoice(BaseModel):
    """Validated extraction. Enforces the semantic rules a JSON schema cannot."""

    vendor_name: str
    invoice_number: str
    document_type: Literal["invoice", "receipt", "purchase_order", "credit_note", "other"]
    currency: str
    conflict_detected: bool = False
    stated_total: float | None = None
    due_date: str | None = None
    document_type_detail: str | None = None
    purchase_order_number: str | None = None
    line_items: list[LineItem] | None = None

    @property
    def calculated_total(self) -> float | None:
        """Sum of the line-item amounts, or None when the doc isn't itemized."""
        if not self.line_items:
            return None
        return round(sum(li.amount for li in self.line_items), 2)

    @model_validator(mode="after")
    def _reconcile_totals(self) -> "Invoice":
        ct = self.calculated_total
        if ct is not None and self.stated_total is not None:
            if abs(ct - self.stated_total) > TOLERANCE and not self.conflict_detected:
                # Retryable: the model most likely mis-read a line amount. Feeding
                # this message back lets it correct the number — or, if the source
                # really disagrees, set conflict_detected=true on the next pass.
                raise ValueError(
                    f"line items sum to {ct} but stated_total is {self.stated_total}; "
                    "re-read the amounts and correct the mis-extracted line item, or "
                    "if the document itself is inconsistent set conflict_detected=true"
                )
        return self


def validate_extraction(data: dict[str, Any]) -> Invoice:
    """Validate a raw extraction dict, raising ``ValidationError`` on failure.

    Raises:
        pydantic.ValidationError: on a schema or semantic (totals) violation.
    """
    return Invoice(**data)


def missing_required_info(data: dict[str, Any]) -> list[str]:
    """Return downstream-required fields that are null/blank in ``data``.

    A non-empty result is the *info-absent* signal: the model already looked and
    reported the field as absent, so retrying the same document cannot help. Route
    these to a human (or an upstream data source) instead of burning retries.
    """
    missing: list[str] = []
    for field in REQUIRED_DOWNSTREAM:
        value = data.get(field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def format_validation_error(exc: ValidationError) -> str:
    """Render a ValidationError as compact, model-readable feedback lines."""
    lines: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ())) or "(root)"
        lines.append(f"- {loc}: {err.get('msg', 'invalid')}")
    return "\n".join(lines)
