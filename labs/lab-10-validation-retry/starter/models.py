"""Invoice extraction model with semantic validation (Lab 10 STARTER).

Implement the semantic validation Task Statement 4.4 describes. Tool use already
removes *syntax* errors (malformed JSON, missing keys, wrong types); your job is
the *semantic* layer a schema cannot express:

  * compute ``calculated_total`` from the line items;
  * compare it to the model-reported ``stated_total``;
  * on a discrepancy, set ``conflict_detected`` and a ``detected_pattern`` label,
    then RAISE a ``ValueError`` whose message names the specific discrepancy (so
    the retry loop can append it as feedback).

Public API (must match solution/): ``LineItem``, ``InvoiceExtraction``,
``TOTAL_TOLERANCE``.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["LineItem", "InvoiceExtraction", "TOTAL_TOLERANCE"]

TOTAL_TOLERANCE = 0.01


class LineItem(BaseModel):
    """One billed line. ``amount`` is what actually feeds the total."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    quantity: float = Field(default=1.0, ge=0)
    unit_price: float = Field(default=0.0, ge=0)
    amount: float = Field(ge=0)


class InvoiceExtraction(BaseModel):
    """Structured invoice extraction with semantic self-correction.

    The fields are defined for you. Implement the ``_reconcile`` validator.
    """

    model_config = ConfigDict(extra="forbid")

    # --- extracted verbatim ------------------------------------------------- #
    vendor_name: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    invoice_date: date
    due_date: date | None = None
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 code")
    line_items: list[LineItem] = Field(min_length=1)
    stated_total: float = Field(ge=0)

    # --- computed by the validator ----------------------------------------- #
    calculated_total: float | None = Field(default=None)

    # --- analysis flags ----------------------------------------------------- #
    conflict_detected: bool = Field(default=False)
    detected_pattern: str | None = Field(default=None)

    @model_validator(mode="after")
    def _reconcile(self) -> "InvoiceExtraction":
        """Semantic validation the schema cannot express.

        TODO:
          1. Compute ``calc = round(sum(item.amount for item in line_items), 2)``
             and assign it to ``self.calculated_total``.
          2. If ``abs(calc - stated_total) > TOTAL_TOLERANCE``: set
             ``conflict_detected=True``, ``detected_pattern="stated_total_mismatch"``,
             and raise ``ValueError`` naming both totals and the pattern label.
          3. If ``due_date`` is set and precedes ``invoice_date``: set the flags
             (pattern ``"due_date_before_invoice_date"``) and raise ``ValueError``.
          4. Return ``self`` when everything reconciles.
        """
        # TODO: implement per the docstring.
        raise NotImplementedError("InvoiceExtraction._reconcile: implement semantic validation")
