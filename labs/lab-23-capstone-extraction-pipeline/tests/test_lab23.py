"""Deterministic tests for Lab 23 — Capstone: Structured Data Extraction Pipeline.

Run the learner's work (default):   uv run pytest lab-23-capstone-extraction-pipeline -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-23-capstone-extraction-pipeline -q

Everything is offline: MockAnthropic scripts the tool_use / text / batch replies,
so the whole pipeline (schema -> extract -> retry -> batch -> routing -> reporting)
is exercised deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from labkit import lab_module
from mock_anthropic import MockAnthropic, text_response, tool_use_response

schema = lab_module(__file__, "schema")
extract_mod = lab_module(__file__, "extract")
batch = lab_module(__file__, "batch_pipeline")

DOCS = Path(__file__).resolve().parent.parent / "docs"


# --------------------------------------------------------------------------- #
# Fixtures / helpers                                                          #
# --------------------------------------------------------------------------- #
def _good() -> dict:
    """A well-formed extraction whose line items sum to the stated total."""
    return {
        "vendor_name": "Blue Heron Supplies",
        "invoice_number": "INV-4501",
        "document_type": "invoice",
        "currency": "USD",
        "conflict_detected": False,
        "stated_total": 160.0,
        "due_date": "2026-06-01",
        "document_type_detail": None,
        "purchase_order_number": None,
        "line_items": [
            {"description": "Drafting paper", "quantity": 5, "unit_price": 12.0, "amount": 60.0},
            {"description": "Ink cartridges", "quantity": 2, "unit_price": 45.0, "amount": 90.0},
            {"description": "Delivery", "quantity": 1, "unit_price": 10.0, "amount": 10.0},
        ],
    }


def _properties(tool: dict) -> dict:
    return tool["input_schema"]["properties"]


def _is_nullable(prop: dict) -> bool:
    t = prop.get("type")
    return isinstance(t, list) and "null" in t


# --------------------------------------------------------------------------- #
# 1. Schema design: nullable + enum "other"                                   #
# --------------------------------------------------------------------------- #
def test_schema_has_nullable_field_and_enum_with_other():
    tool = schema.build_extraction_tool()
    props = _properties(tool)

    nullable = [name for name, p in props.items() if _is_nullable(p)]
    assert nullable, "expected at least one nullable field (type list containing 'null')"

    enums_with_other = [
        name for name, p in props.items()
        if isinstance(p.get("enum"), list) and "other" in p["enum"]
    ]
    assert enums_with_other, "expected an enum field containing 'other'"

    # required + optional both present
    required = set(tool["input_schema"]["required"])
    assert required, "schema must declare required fields"
    assert set(props) - required, "schema must also have optional (non-required) fields"


def test_build_extraction_tool_returns_independent_copies():
    a = schema.build_extraction_tool()
    a["input_schema"]["properties"].clear()
    b = schema.build_extraction_tool()
    assert b["input_schema"]["properties"], "build_extraction_tool must return a copy"


# --------------------------------------------------------------------------- #
# 2. Semantic validation (Pydantic)                                           #
# --------------------------------------------------------------------------- #
def test_validate_accepts_consistent_extraction():
    invoice = schema.validate_extraction(_good())
    assert invoice.calculated_total == 160.0
    assert invoice.stated_total == 160.0


def test_validate_raises_on_totals_mismatch():
    bad = _good()
    bad["line_items"][0]["amount"] = 55.0  # now sums to 155, not 160
    with pytest.raises(schema.ValidationError):
        schema.validate_extraction(bad)


def test_conflict_detected_suppresses_totals_error():
    """A genuinely inconsistent source (flagged) is kept, not retried away."""
    flagged = _good()
    flagged["line_items"][0]["amount"] = 55.0  # sums to 155 != 160
    flagged["conflict_detected"] = True
    invoice = schema.validate_extraction(flagged)  # must NOT raise
    assert invoice.conflict_detected is True
    assert invoice.calculated_total != invoice.stated_total


def test_missing_required_info_flags_absent_downstream_fields():
    data = _good()
    data["stated_total"] = None
    data["vendor_name"] = ""
    missing = schema.missing_required_info(data)
    assert "stated_total" in missing
    assert "vendor_name" in missing


# --------------------------------------------------------------------------- #
# 3. extract(): tool_use, few-shot, null pass-through                          #
# --------------------------------------------------------------------------- #
def test_extract_forces_tool_and_returns_input_with_few_shot():
    tool = schema.build_extraction_tool()
    client = MockAnthropic(responses=[tool_use_response(tool["name"], _good())])

    result = extract_mod.extract(client, "some invoice text")

    assert result == _good()
    call = client.calls[0]
    assert call["tools"] == [tool]
    assert call["tool_choice"] == {"type": "tool", "name": tool["name"]}
    # Few-shot demonstration turns precede the real document turn.
    assert len(call["messages"]) > 1
    assert any(m["role"] == "assistant" for m in call["messages"]), "few-shot turns expected"


def test_extract_can_disable_few_shot():
    tool = schema.build_extraction_tool()
    client = MockAnthropic(responses=[tool_use_response(tool["name"], _good())])
    extract_mod.extract(client, "doc", few_shot=False)
    msgs = client.calls[0]["messages"]
    assert all(m["role"] == "user" for m in msgs), "no few-shot turns when disabled"


def test_extract_passes_through_null_without_fabricating():
    tool = schema.build_extraction_tool()
    absent = _good()
    absent["due_date"] = None
    client = MockAnthropic(responses=[tool_use_response(tool["name"], absent)])
    result = extract_mod.extract(client, "invoice with no due date")
    assert result["due_date"] is None


def test_extract_returns_none_on_plain_text():
    client = MockAnthropic(responses=[text_response("I can help with that.")])
    assert extract_mod.extract(client, "hello", tool_choice="auto") is None


# --------------------------------------------------------------------------- #
# 4. Validation-retry loop                                                     #
# --------------------------------------------------------------------------- #
def test_retry_succeeds_after_appended_validation_error():
    """First pass mis-sums; error feedback is appended; second pass is corrected."""
    tool = schema.build_extraction_tool()
    bad = _good()
    bad["line_items"][0]["amount"] = 55.0  # sums to 155 != 160 -> validation error
    good = _good()  # corrected

    client = MockAnthropic(responses=[
        tool_use_response(tool["name"], bad),
        tool_use_response(tool["name"], good),
    ])

    result = extract_mod.extract_with_retry(client, "invoice text", max_retries=2)

    assert result["status"] == "ok"
    assert result["attempts"] == 2
    assert len(client.calls) == 2
    # The retry request carried the specific validation error back to the model.
    retry_messages = client.calls[1]["messages"]
    joined = "\n".join(m["content"] for m in retry_messages if isinstance(m["content"], str))
    assert "stated_total" in joined and "155" in joined


def test_retry_gives_up_immediately_when_info_absent():
    """A downstream-required null means retry is futile — don't burn attempts."""
    tool = schema.build_extraction_tool()
    absent = _good()
    absent["stated_total"] = None  # document never stated a total

    # Script extra responses to prove they are NOT consumed.
    client = MockAnthropic(responses=[
        tool_use_response(tool["name"], absent),
        tool_use_response(tool["name"], _good()),
    ])

    result = extract_mod.extract_with_retry(client, "cover page only", max_retries=3)

    assert result["status"] == "gave_up"
    assert result["reason"] == "info_absent"
    assert "stated_total" in result["missing_fields"]
    assert result["attempts"] == 1
    assert len(client.calls) == 1  # no wasted retries


# --------------------------------------------------------------------------- #
# 5. Batch pipeline: custom_id correlation + resubmit-only-failures + chunking #
# --------------------------------------------------------------------------- #
def _batch_handler_factory(fail_ids: set[str]):
    def handler(custom_id, params):
        if custom_id in fail_ids:
            return ("errored", {"type": "invalid_request", "message": "context too long"})
        return ("succeeded", tool_use_response("extract_invoice", _good()))
    return handler


def test_build_requests_unique_custom_ids():
    reqs = batch.build_requests([{"id": "d1", "text": "a"}, {"id": "d2", "text": "b"}])
    assert [r["custom_id"] for r in reqs] == ["d1", "d2"]
    with pytest.raises(ValueError):
        batch.build_requests([{"id": "dup", "text": "a"}, {"id": "dup", "text": "b"}])


def test_submit_and_collect_separates_by_custom_id():
    client = MockAnthropic(batch_handler=_batch_handler_factory({"d2"}))
    docs = [{"id": "d1", "text": "ok doc"}, {"id": "d2", "text": "bad doc"}]
    out = batch.submit_and_collect(client, batch.build_requests(docs))
    assert set(out["succeeded"]) == {"d1"}
    assert out["failed"] == ["d2"]


def test_resubmit_failed_resends_only_failures_and_chunks_oversized():
    documents = [
        {"id": "d1", "text": "ok doc"},
        {"id": "d2", "text": "X" * 1200, "oversized": True},  # must be chunked
    ]
    # First batch: d2 fails (too long). Second batch: chunks succeed.
    first = MockAnthropic(batch_handler=_batch_handler_factory({"d2"}))
    out1 = batch.submit_and_collect(first, batch.build_requests(documents))
    assert out1["failed"] == ["d2"]

    second = MockAnthropic(batch_handler=_batch_handler_factory(set()))
    out2 = batch.resubmit_failed(second, out1["failed"], documents, chunk_chars=500)

    sent_ids = [r.custom_id for r in second.messages.batches._batches["msgbatch_1"]._requests]
    # Only the failed doc was resent — d1 is NOT in the resubmission.
    assert all(cid.startswith("d2") for cid in sent_ids)
    # 1200 chars / 500 -> 3 chunks.
    assert sent_ids == ["d2#chunk-0", "d2#chunk-1", "d2#chunk-2"]
    assert set(out2["succeeded"]) == {"d2#chunk-0", "d2#chunk-1", "d2#chunk-2"}


def test_choose_api_and_submission_frequency():
    assert batch.choose_api({"blocking": True}) == "sync"
    assert batch.choose_api({"latency_tolerance": "overnight"}) == "batch"
    assert batch.submission_frequency(30, batch_window_hours=24) == 6
    with pytest.raises(ValueError):
        batch.submission_frequency(20, batch_window_hours=24)


# --------------------------------------------------------------------------- #
# 6. Human-review routing                                                      #
# --------------------------------------------------------------------------- #
def test_route_for_review_sends_low_confidence_and_conflict_to_human():
    records = [
        {  # confident, consistent -> automated
            "custom_id": "a",
            "extraction": _good(),
            "field_confidence": {"vendor_name": 0.98, "stated_total": 0.95},
            "conflict_detected": False,
        },
        {  # one low-confidence field -> review
            "custom_id": "b",
            "extraction": _good(),
            "field_confidence": {"vendor_name": 0.98, "stated_total": 0.40},
            "conflict_detected": False,
        },
        {  # flagged source conflict -> review
            "custom_id": "c",
            "extraction": _good(),
            "field_confidence": {"vendor_name": 0.99, "stated_total": 0.99},
            "conflict_detected": True,
        },
    ]
    out = batch.route_for_review(records, confidence_threshold=0.75)
    assert [r["custom_id"] for r in out["auto"]] == ["a"]
    review_ids = {r["custom_id"] for r in out["review"]}
    assert review_ids == {"b", "c"}
    reasons_b = next(r["reasons"] for r in out["review"] if r["custom_id"] == "b")
    assert any("low_confidence" in why for why in reasons_b)


def test_route_for_review_flags_info_absent_extractions():
    absent = _good()
    absent["stated_total"] = None
    records = [{
        "custom_id": "z",
        "extraction": absent,
        "field_confidence": {"vendor_name": 0.99},
        "conflict_detected": False,
    }]
    out = batch.route_for_review(records)
    assert not out["auto"]
    reasons = out["review"][0]["reasons"]
    assert any("info_absent" in why for why in reasons)


# --------------------------------------------------------------------------- #
# 7. Accuracy by segment reveals the poor segment behind a high aggregate      #
# --------------------------------------------------------------------------- #
def test_accuracy_by_segment_reveals_poor_segment():
    data = json.loads((DOCS / "labeled_set.json").read_text())
    report = batch.accuracy_by_segment(
        data["records"], segment_field="document_type", fields=data["scored_fields"]
    )
    # High aggregate...
    assert report["overall"] >= 0.85
    # ...but one segment is quietly failing.
    assert report["worst_segment"] == "handwritten"
    assert report["by_segment"]["handwritten"] <= 0.3
    assert report["by_segment"]["typed_invoice"] == 1.0


def test_accuracy_by_segment_defaults_fields_to_label_keys():
    records = [
        {"document_type": "x", "prediction": {"a": 1, "b": 2}, "label": {"a": 1, "b": 9}},
    ]
    report = batch.accuracy_by_segment(records)
    assert report["by_segment"]["x"] == 0.5  # 1 of 2 fields correct


# --------------------------------------------------------------------------- #
# 8. Fixtures exist and are usable end-to-end                                  #
# --------------------------------------------------------------------------- #
def test_clean_invoice_fixture_extracts_end_to_end():
    tool = schema.build_extraction_tool()
    doc = (DOCS / "clean_invoice.txt").read_text()
    client = MockAnthropic(responses=[tool_use_response(tool["name"], _good())])
    result = extract_mod.extract_with_retry(client, doc, max_retries=1)
    assert result["status"] == "ok"
    assert result["invoice"].invoice_number == "INV-4501"
