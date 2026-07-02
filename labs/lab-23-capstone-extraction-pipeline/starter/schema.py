"""Extraction schema + semantic validation (Lab 23 capstone — STARTER).

Implement the extraction contract that the whole pipeline depends on:

1. STRUCTURAL LAYER — the tool ``input_schema`` (Task Statement 4.3):
   * required vs optional fields,
   * *nullable* required fields (type list containing "null") so the model returns
     null when info is absent instead of fabricating,
   * an enum with an "other" escape hatch + a free-text detail field.

2. SEMANTIC LAYER — the :class:`Invoice` Pydantic model (Task Statement 4.4):
   * derive ``calculated_total`` from ``line_items`` and compare to ``stated_total``,
   * RAISE on a mismatch (a retryable transcription error) UNLESS the model set
     ``conflict_detected=True`` (a genuine source inconsistency to route to a human).

Also implement :func:`missing_required_info` — the "information absent from source"
signal that makes a retry futile.

Keep the public names below; the tests import them. Replace each ``raise
NotImplementedError`` with a real implementation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ValidationError, model_validator

__all__ = [
    "TOOL_NAME",
    "DOCUMENT_TYPES",
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
DOCUMENT_TYPES = ["invoice", "receipt", "purchase_order", "credit_note", "other"]
REQUIRED_DOWNSTREAM = ["vendor_name", "invoice_number", "currency", "stated_total"]
TOLERANCE = 0.01


def build_extraction_tool() -> dict[str, Any]:
    """Return the extraction tool definition (name, description, input_schema).

    The input_schema must include: at least one nullable field, an enum with an
    'other' value, and a mix of required and optional fields. Return a COPY so
    callers can't corrupt a shared object.
    """
    raise NotImplementedError("Lab 23: implement build_extraction_tool")


class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float


class Invoice(BaseModel):
    """Validated extraction — enforce the semantic rules a JSON schema cannot.

    TODO: declare the fields (vendor_name, invoice_number, document_type,
    currency, conflict_detected, stated_total, due_date, document_type_detail,
    purchase_order_number, line_items), add a ``calculated_total`` property, and a
    model_validator that raises on a totals mismatch unless conflict_detected.
    """

    # Minimal stub so the module imports; replace with the full model.
    vendor_name: str
    invoice_number: str
    document_type: Literal["invoice", "receipt", "purchase_order", "credit_note", "other"]
    currency: str

    @model_validator(mode="after")
    def _reconcile_totals(self) -> "Invoice":
        raise NotImplementedError("Lab 23: implement the totals reconciliation validator")


def validate_extraction(data: dict[str, Any]) -> Invoice:
    """Validate a raw extraction dict, raising ValidationError on failure."""
    raise NotImplementedError("Lab 23: implement validate_extraction")


def missing_required_info(data: dict[str, Any]) -> list[str]:
    """Return downstream-required fields that are null/blank (info-absent signal)."""
    raise NotImplementedError("Lab 23: implement missing_required_info")


def format_validation_error(exc: ValidationError) -> str:
    """Render a ValidationError as compact, model-readable feedback lines."""
    raise NotImplementedError("Lab 23: implement format_validation_error")
