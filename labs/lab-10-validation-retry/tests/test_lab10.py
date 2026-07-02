"""Deterministic tests for Lab 10 — Validation, Retry & Feedback Loops.

Run the learner's work (default):   uv run pytest lab-10-validation-retry -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-10-validation-retry -q
"""

from __future__ import annotations

from pathlib import Path

import pytest
from labkit import lab_module
from mock_anthropic import MockAnthropic, tool_use_response
from pydantic import ValidationError

models = lab_module(__file__, "models")
retry = lab_module(__file__, "retry")

DOCS = Path(__file__).resolve().parent.parent / "docs"
TOOL_NAME = "record_invoice"


# --------------------------------------------------------------------------- #
# Fixtures / helpers                                                          #
# --------------------------------------------------------------------------- #
def _good_extraction() -> dict:
    return {
        "vendor_name": "Acme Widgets LLC",
        "invoice_number": "INV-2201",
        "invoice_date": "2026-06-01",
        "due_date": "2026-07-01",
        "currency": "USD",
        "line_items": [
            {"description": "Steel widget", "quantity": 10, "unit_price": 12.5, "amount": 125.0},
            {"description": "Rubber gasket", "quantity": 4, "unit_price": 5.0, "amount": 20.0},
            {"description": "Freight", "quantity": 1, "unit_price": 30.0, "amount": 30.0},
        ],
        "stated_total": 175.0,
    }


def _tool_resp(data: dict):
    return tool_use_response(TOOL_NAME, data)


def _serialize(messages) -> str:
    return str(messages)


# --------------------------------------------------------------------------- #
# 1. The Pydantic validator catches semantic errors a schema cannot           #
# --------------------------------------------------------------------------- #
def test_validator_accepts_reconciling_invoice():
    inv = models.InvoiceExtraction.model_validate(_good_extraction())
    assert inv.calculated_total == 175.0
    assert inv.conflict_detected is False
    assert inv.detected_pattern is None


def test_validator_catches_sum_mismatch():
    bad = _good_extraction()
    bad["stated_total"] = 999.0  # does not equal the 175.0 sum of line items
    with pytest.raises(ValidationError) as exc:
        models.InvoiceExtraction.model_validate(bad)
    msg = str(exc.value)
    # The message names BOTH numbers and the detected_pattern label so a retry
    # (or a human) sees the specific discrepancy.
    assert "999" in msg and "175" in msg
    assert "stated_total_mismatch" in msg


def test_validator_catches_date_conflict():
    bad = _good_extraction()
    bad["due_date"] = "2026-05-01"  # before the 2026-06-01 invoice_date
    with pytest.raises(ValidationError) as exc:
        models.InvoiceExtraction.model_validate(bad)
    assert "due_date_before_invoice_date" in str(exc.value)


# --------------------------------------------------------------------------- #
# 2. is_retryable_error mapping                                                #
# --------------------------------------------------------------------------- #
def test_is_retryable_error_mapping():
    assert retry.is_retryable_error("format") is True
    assert retry.is_retryable_error("structural") is True
    assert retry.is_retryable_error("info_absent") is False
    assert retry.is_retryable_error("source_conflict") is False


def test_is_retryable_error_rejects_unknown_kind():
    with pytest.raises(ValueError):
        retry.is_retryable_error("not_a_kind")


# --------------------------------------------------------------------------- #
# 3. Retry succeeds on attempt 2 AND appends the specific error as feedback    #
# --------------------------------------------------------------------------- #
def test_retry_with_feedback_succeeds_on_second_attempt():
    # First extraction has a bad (non-ISO) date -> a FORMAT error (retryable).
    bad = _good_extraction()
    bad["invoice_date"] = "06/01/2026"
    good = _good_extraction()

    client = MockAnthropic(responses=[_tool_resp(bad), _tool_resp(good)])
    document = (DOCS / "clean.txt").read_text()

    result = retry.extract_with_retry(client, document, max_retries=2)

    assert result["succeeded"] is True
    assert result["attempts"] == 2
    assert result["data"]["calculated_total"] == 175.0

    # Exactly two model calls were made.
    assert len(client.calls) == 2

    # The SPECIFIC validation error was appended to the SECOND request.
    retry_messages = _serialize(client.calls[1]["messages"])
    assert "invoice_date" in retry_messages
    # The original document is still present on the retry (self-correction needs it).
    assert "ACME WIDGETS" in retry_messages
    # The first request did NOT carry any error feedback.
    assert "FAILED validation" not in _serialize(client.calls[0]["messages"])


# --------------------------------------------------------------------------- #
# 4. Info-absent: retry is futile -> give up instead of looping                #
# --------------------------------------------------------------------------- #
def test_info_absent_does_not_retry_pointlessly():
    document = (DOCS / "missing_field.txt").read_text()

    # The extraction omits invoice_number; the document has no invoice number
    # anywhere, so re-asking cannot fix it.
    missing = _good_extraction()
    del missing["invoice_number"]

    client = MockAnthropic(responses=[_tool_resp(missing), _tool_resp(missing)])
    result = retry.extract_with_retry(client, document, max_retries=2)

    assert result["succeeded"] is False
    # Gave up after the FIRST attempt rather than burning the retry budget.
    assert result["attempts"] == 1
    assert len(client.calls) == 1


def test_should_retry_false_for_info_absent():
    document = (DOCS / "missing_field.txt").read_text()
    missing = _good_extraction()
    del missing["invoice_number"]
    try:
        models.InvoiceExtraction.model_validate(missing)
    except ValidationError as err:
        assert retry.should_retry(document, err) is False
    else:  # pragma: no cover - the extraction is invalid, this branch is a bug
        pytest.fail("expected the extraction to fail validation")


def test_should_retry_true_when_field_present_in_source():
    # Same missing field, but a document that DOES contain the info -> structural,
    # so a retry is worth attempting.
    document = "Invoice #: INV-999\nEspresso = 3.50\nTotal due: 3.50\n"
    missing = _good_extraction()
    del missing["invoice_number"]
    try:
        models.InvoiceExtraction.model_validate(missing)
    except ValidationError as err:
        assert retry.should_retry(document, err) is True


def test_source_conflict_is_not_retryable():
    document = (DOCS / "total_mismatch.txt").read_text()
    bad = _good_extraction()
    bad["stated_total"] = 3950.0
    bad["line_items"] = [
        {"description": "Consulting", "quantity": 20, "unit_price": 150.0, "amount": 3000.0},
        {"description": "Travel", "quantity": 1, "unit_price": 450.0, "amount": 450.0},
    ]
    client = MockAnthropic(responses=[_tool_resp(bad), _tool_resp(bad), _tool_resp(bad)])

    result = retry.extract_with_retry(client, document, max_retries=2)

    assert result["succeeded"] is False
    assert result["attempts"] == 1  # source conflict -> no pointless retries
    assert result["detected_pattern"] == "stated_total_mismatch"


# --------------------------------------------------------------------------- #
# 5. Clean document succeeds on the first attempt (no retry needed)            #
# --------------------------------------------------------------------------- #
def test_clean_document_succeeds_first_try():
    client = MockAnthropic(responses=[_tool_resp(_good_extraction())])
    document = (DOCS / "clean.txt").read_text()
    result = retry.extract_with_retry(client, document, max_retries=2)
    assert result["succeeded"] is True
    assert result["attempts"] == 1
    assert len(client.calls) == 1
