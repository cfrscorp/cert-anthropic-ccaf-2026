"""Invoice extraction model with semantic validation (Lab 10 reference solution).

Task Statement 4.4 draws a sharp line between two failure classes:

* **Schema / syntax errors** — malformed JSON, missing keys, wrong types. These
  are *eliminated by tool use*: when Claude fills a tool's ``input_schema`` the
  API guarantees the shape. We still declare the shape here (Pydantic types) so
  that if a raw dict does slip through it is caught, but in the tool-use path
  these never fire.
* **Semantic errors** — the JSON is well-formed but *wrong in meaning*: the line
  items do not sum to the stated total, a value landed in the wrong field, or two
  source values contradict each other. No schema can catch these; you need a
  validator that understands the domain.

This model implements the canonical self-correction flow from the guide:

* it computes ``calculated_total`` from the line items and compares it to the
  model-reported ``stated_total`` (``calculated_total`` vs ``stated_total``);
* on a discrepancy it sets ``conflict_detected`` and a ``detected_pattern`` label
  (for downstream false-positive / dismissal analysis) and raises a
  ``ValidationError`` whose message names the *specific* discrepancy so a retry
  can append it as feedback.

``detected_pattern`` is the field the guide calls for: a stable label naming
*which* construct triggered the finding, so you can aggregate how often each
pattern turns out to be a true problem versus a false positive.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["LineItem", "InvoiceExtraction", "TOTAL_TOLERANCE"]

# Money reconciliation tolerance (rounding noise, not a real discrepancy).
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

    Fields fall into three groups:

    * **Extracted verbatim** from the document: ``vendor_name``,
      ``invoice_number``, ``invoice_date``, ``due_date``, ``currency``,
      ``line_items``, ``stated_total``.
    * **Computed** by the validator: ``calculated_total`` (sum of line items).
    * **Analysis** flags the validator (or the model) sets to describe a finding:
      ``conflict_detected`` and ``detected_pattern``.
    """

    # extra="forbid" turns an unexpected key (a structural error) into a caught
    # validation error rather than a silently-ignored field.
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
    calculated_total: float | None = Field(
        default=None,
        description="Sum of line_items amounts; filled in by the validator.",
    )

    # --- analysis flags (self-correction / false-positive analysis) -------- #
    conflict_detected: bool = Field(
        default=False,
        description="True when the source data is internally inconsistent.",
    )
    detected_pattern: str | None = Field(
        default=None,
        description=(
            "Stable label naming which check triggered a finding, e.g. "
            "'stated_total_mismatch'. Enables aggregate false-positive analysis."
        ),
    )

    @model_validator(mode="after")
    def _reconcile(self) -> "InvoiceExtraction":
        """Semantic validation the schema cannot express.

        Computes ``calculated_total`` and flags two source-conflict patterns:
        a stated/calculated total mismatch, and a due date before the invoice
        date. Both raise so the retry loop can surface the specific message.
        """
        calc = round(sum(item.amount for item in self.line_items), 2)
        self.calculated_total = calc

        # Pattern 1: the stated total does not equal the sum of the line items.
        if abs(calc - self.stated_total) > TOTAL_TOLERANCE:
            self.conflict_detected = True
            self.detected_pattern = "stated_total_mismatch"
            raise ValueError(
                f"stated_total ({self.stated_total}) does not equal "
                f"calculated_total ({calc}), the sum of {len(self.line_items)} "
                f"line item amounts. Re-check each line item amount and the "
                f"stated total so they reconcile "
                f"[detected_pattern=stated_total_mismatch]."
            )

        # Pattern 2: the due date precedes the invoice date (contradictory dates).
        if self.due_date is not None and self.due_date < self.invoice_date:
            self.conflict_detected = True
            self.detected_pattern = "due_date_before_invoice_date"
            raise ValueError(
                f"due_date ({self.due_date.isoformat()}) is before invoice_date "
                f"({self.invoice_date.isoformat()}); the dates contradict each "
                f"other [detected_pattern=due_date_before_invoice_date]."
            )

        return self
