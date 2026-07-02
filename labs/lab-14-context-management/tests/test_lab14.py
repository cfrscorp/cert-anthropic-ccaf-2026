"""Deterministic tests for L14 — Context Management & Preservation.

These exercise the context-engineering primitives from Task Statements 5.1 and
5.4: pulling transactional facts into a persistent case-facts block, trimming
verbose tool output, placing a summary first to beat "lost in the middle", and
persisting scratchpad/manifest state for crash recovery.

Run from labs/:  uv run pytest lab-14-context-management
Validate ref:     LAB_TARGET=solution uv run pytest lab-14-context-management
"""

from __future__ import annotations

import json
from pathlib import Path

from labkit import lab_module

ctx = lab_module(__file__, "context")

LAB_DIR = Path(__file__).resolve().parent.parent


def _fixture(name: str):
    return json.loads((LAB_DIR / name).read_text(encoding="utf-8"))


# --- 5.1: extract transactional facts into a persistent block --------------


def test_extract_case_facts_retains_numeric_date_order_status():
    conversation = _fixture("sample_conversation.json")
    facts = ctx.extract_case_facts(conversation)

    # Amounts kept verbatim (a vague summary would blur "$45.50" into "~$45").
    assert "$129.99" in facts["amounts"]
    assert "$45.50" in facts["amounts"]

    # Dates preserved exactly, not collapsed to "in June".
    assert "2026-06-15" in facts["dates"]
    assert "2026-06-22" in facts["dates"]

    # Order numbers preserved (the "#" prefix is not part of the id).
    assert "A-10432" in facts["order_numbers"]
    assert "ORD-77219" in facts["order_numbers"]

    # Statuses captured from the known vocabulary.
    assert "delivered" in facts["statuses"]
    assert "in transit" in facts["statuses"]


def test_extract_case_facts_dedupes_values():
    conversation = [
        {"role": "user", "content": "Order A-10432 for $10.00 was delivered."},
        {"role": "assistant", "content": "Yes, A-10432 shows delivered."},
    ]
    facts = ctx.extract_case_facts(conversation)
    assert facts["order_numbers"] == ["A-10432"]
    assert facts["statuses"].count("delivered") == 1


# --- 5.1: trim verbose tool output (40+ fields -> 5) -----------------------


def test_trim_tool_output_keeps_only_requested_fields():
    raw = _fixture("sample_order_lookup.json")
    assert len(raw) >= 40  # the fixture really is verbose

    relevant = ["order_id", "status", "order_total", "customer_email", "return_eligible"]
    trimmed = ctx.trim_tool_output(raw, relevant)

    # Exactly the requested fields survive, with their original values.
    assert set(trimmed.keys()) == set(relevant)
    assert trimmed["order_id"] == "ORD-77219"
    assert trimmed["status"] == "delivered"
    assert trimmed["order_total"] == 45.50
    assert trimmed["return_eligible"] is True

    # Irrelevant, token-hungry fields are dropped.
    assert "internal_notes" not in trimmed
    assert "billing_address_line1" not in trimmed
    assert "line_items" not in trimmed


def test_trim_tool_output_skips_absent_fields():
    trimmed = ctx.trim_tool_output({"a": 1, "b": 2}, ["a", "missing"])
    assert trimmed == {"a": 1}


# --- 5.1: mitigate "lost in the middle" — summary first --------------------


def test_order_for_position_puts_summary_first():
    sections = [
        {"title": "Order A-10432", "summary": "in transit, ETA 2026-07-05", "detail": "..." * 50},
        {"title": "Order ORD-77219", "summary": "refunded $45.50", "detail": "..." * 50},
    ]
    ordered = ctx.order_for_position(sections)

    # The synthesized summary is at index 0.
    assert ordered[0]["header"] == "Key Findings"
    assert "Order A-10432" in ordered[0]["body"]
    assert "refunded $45.50" in ordered[0]["body"]

    # Every element carries an explicit header, and detail sections follow.
    assert all(item.get("header") for item in ordered)
    assert len(ordered) == len(sections) + 1
    assert ordered[1]["header"] == "Order A-10432"
    assert ordered[-1]["header"] == "Order ORD-77219"


# --- 5.4: crash-recoverable scratchpad + manifest --------------------------


def test_scratchpad_persists_across_new_instances(tmp_path):
    path = tmp_path / "scratchpad.json"

    pad = ctx.Scratchpad(path)
    pad.record("refund_amount", "$45.50")
    pad.record("open_orders", ["A-10432"])

    # A fresh instance (simulating a new process after a crash) recalls it.
    reopened = ctx.Scratchpad(path)
    assert reopened.recall("refund_amount") == "$45.50"
    assert reopened.recall("open_orders") == ["A-10432"]

    # State was actually flushed to disk as JSON.
    assert path.exists()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["refund_amount"] == "$45.50"


def test_scratchpad_recall_default(tmp_path):
    pad = ctx.Scratchpad(tmp_path / "s.json")
    assert pad.recall("nope") is None
    assert pad.recall("nope", "fallback") == "fallback"


def test_load_manifest(tmp_path):
    manifest = {
        "session": "support-2026-07-02",
        "agents": {"order_agent": {"state": "done", "findings": 2}},
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = ctx.load_manifest(path)
    assert loaded == manifest
    assert loaded["agents"]["order_agent"]["state"] == "done"
