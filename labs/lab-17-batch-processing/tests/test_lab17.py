"""Deterministic tests for Lab 17 — Batch Processing Strategies.

Run the learner's work (default):   uv run pytest lab-17-batch-processing -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-17-batch-processing -q
"""

from __future__ import annotations

import pytest
from labkit import lab_module
from mock_anthropic import MockAnthropic, text_response

# Load batch.py from starter/ (default) or solution/ (LAB_TARGET=solution).
mod = lab_module(__file__, "batch")


DOCUMENTS = [
    {"id": "doc-1", "text": "quarterly report body one"},
    {"id": "doc-2", "text": "quarterly report body two"},
    {"id": "doc-3", "text": "x" * 1200, "oversized": True},
]


def _all_succeed(custom_id, params):
    return ("succeeded", text_response(f"summary of {custom_id}"))


def _fail(*ids):
    """A batch handler that errors the given custom_ids, succeeds the rest."""
    targets = set(ids)

    def handler(custom_id, params):
        if custom_id in targets:
            return ("errored", {"type": "invalid_request", "message": "too long"})
        return ("succeeded", text_response(f"summary of {custom_id}"))

    return handler


# --------------------------------------------------------------------------- #
# build_requests                                                              #
# --------------------------------------------------------------------------- #
def test_build_requests_one_per_document_with_unique_custom_ids():
    requests = mod.build_requests(DOCUMENTS)
    assert len(requests) == len(DOCUMENTS)
    ids = [r["custom_id"] for r in requests]
    assert ids == ["doc-1", "doc-2", "doc-3"]
    assert len(set(ids)) == len(ids)  # unique


def test_build_requests_params_are_well_formed():
    requests = mod.build_requests(DOCUMENTS[:1])
    params = requests[0]["params"]
    assert "model" in params and params["model"]
    assert isinstance(params["max_tokens"], int) and params["max_tokens"] > 0
    assert params["messages"][0]["role"] == "user"
    assert "report body one" in params["messages"][0]["content"]


def test_build_requests_rejects_duplicate_ids():
    dupes = [{"id": "dup", "text": "a"}, {"id": "dup", "text": "b"}]
    with pytest.raises(ValueError):
        mod.build_requests(dupes)


# --------------------------------------------------------------------------- #
# submit_and_collect                                                          #
# --------------------------------------------------------------------------- #
def test_submit_and_collect_all_succeed():
    client = MockAnthropic(batch_handler=_all_succeed)
    requests = mod.build_requests(DOCUMENTS)

    out = mod.submit_and_collect(client, requests)

    assert set(out["succeeded"]) == {"doc-1", "doc-2", "doc-3"}
    assert out["failed"] == []


def test_submit_and_collect_separates_failed_by_custom_id():
    client = MockAnthropic(batch_handler=_fail("doc-3"))
    requests = mod.build_requests(DOCUMENTS)

    out = mod.submit_and_collect(client, requests)

    assert out["failed"] == ["doc-3"]
    assert set(out["succeeded"]) == {"doc-1", "doc-2"}
    assert "doc-3" not in out["succeeded"]


# --------------------------------------------------------------------------- #
# resubmit_failed                                                             #
# --------------------------------------------------------------------------- #
def test_resubmit_failed_only_resends_failed_ids():
    """Only doc-2 failed; the resubmission must not touch doc-1 or doc-3."""
    sent: list[str] = []

    def spy(custom_id, params):
        sent.append(custom_id)
        return ("succeeded", text_response("ok"))

    client = MockAnthropic(batch_handler=spy)
    out = mod.resubmit_failed(client, ["doc-2"], DOCUMENTS)

    assert sent == ["doc-2"]  # ONLY the failed doc was resubmitted
    assert set(out["succeeded"]) == {"doc-2"}
    assert out["failed"] == []


def test_resubmit_failed_chunks_oversized_document():
    """doc-3 is oversized (1200 chars) and must be split into >1 chunk."""
    sent: list[str] = []

    def spy(custom_id, params):
        sent.append(custom_id)
        return ("succeeded", text_response("ok"))

    client = MockAnthropic(batch_handler=spy)
    out = mod.resubmit_failed(client, ["doc-3"], DOCUMENTS, chunk_oversized=True)

    assert len(sent) > 1, "oversized doc should be chunked into multiple requests"
    assert all(cid.startswith("doc-3") for cid in sent)
    assert len(set(sent)) == len(sent), "chunk custom_ids must stay unique"
    assert set(out["succeeded"]) == set(sent)


def test_resubmit_failed_can_disable_chunking():
    sent: list[str] = []

    def spy(custom_id, params):
        sent.append(custom_id)
        return ("succeeded", text_response("ok"))

    client = MockAnthropic(batch_handler=spy)
    mod.resubmit_failed(client, ["doc-3"], DOCUMENTS, chunk_oversized=False)

    assert sent == ["doc-3"]  # no chunking -> single request


# --------------------------------------------------------------------------- #
# choose_api  (Sample Question 11 cases)                                      #
# --------------------------------------------------------------------------- #
def test_choose_api_blocking_pre_merge_is_sync():
    assert mod.choose_api({"name": "pre-merge check", "blocking": True}) == "sync"


def test_choose_api_overnight_report_is_batch():
    assert (
        mod.choose_api({"name": "tech debt report", "latency_tolerance": "overnight"})
        == "batch"
    )


def test_choose_api_weekly_audit_is_batch():
    assert mod.choose_api({"latency_tolerance": "weekly"}) == "batch"


def test_choose_api_blocking_tolerance_string_is_sync():
    assert mod.choose_api({"latency_tolerance": "blocking"}) == "sync"


def test_choose_api_requires_a_latency_signal():
    with pytest.raises(ValueError):
        mod.choose_api({"name": "no signal"})


# --------------------------------------------------------------------------- #
# submission_frequency                                                        #
# --------------------------------------------------------------------------- #
def test_submission_frequency_30h_sla_24h_window_is_6h():
    assert mod.submission_frequency(30, 24) == 6.0


def test_submission_frequency_48h_sla_24h_window_is_24h():
    assert mod.submission_frequency(48, 24) == 24.0


def test_submission_frequency_default_window_is_24h():
    # 36h SLA, default 24h window -> 12h.
    assert mod.submission_frequency(36) == 12.0


def test_submission_frequency_unmeetable_sla_raises():
    # SLA not larger than the batch window cannot be met.
    with pytest.raises(ValueError):
        mod.submission_frequency(24, 24)
