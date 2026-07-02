"""Batch extraction + human-review routing + accuracy reporting (Lab 23 — STARTER).

Implement:

* ``build_requests(documents)`` — self-contained batch requests, unique ``custom_id``.
* ``submit_and_collect(client, requests)`` — submit, split succeeded/failed BY custom_id.
* ``resubmit_failed(client, failed_ids, documents, *, chunk_oversized=True,
  chunk_chars=500)`` — resend only failures, chunking any flagged ``oversized``.
* ``choose_api(workflow)`` / ``submission_frequency(sla_hours, batch_window_hours=24)``.
* ``route_for_review(records, *, confidence_threshold=0.75)`` — send low-confidence,
  conflict, and info-absent extractions to human review.
* ``accuracy_by_segment(records, *, segment_field="document_type", fields=None)`` —
  field-level accuracy overall and per segment, exposing the worst segment.

Callers inject ``client`` (real SDK or MockAnthropic). Do not construct one here.
"""

from __future__ import annotations

from typing import Any

from schema import build_extraction_tool, missing_required_info  # noqa: F401

__all__ = [
    "build_requests",
    "submit_and_collect",
    "resubmit_failed",
    "choose_api",
    "submission_frequency",
    "route_for_review",
    "accuracy_by_segment",
]

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1500


def build_requests(documents: list[dict]) -> list[dict]:
    """Turn documents into Message Batches requests with a unique custom_id each."""
    raise NotImplementedError("Lab 23: implement build_requests")


def submit_and_collect(client: Any, requests: list[dict]) -> dict:
    """Submit a batch; return {"succeeded": {id: msg}, "failed": [id, ...]}."""
    raise NotImplementedError("Lab 23: implement submit_and_collect")


def resubmit_failed(
    client: Any,
    failed_ids: list[str],
    documents: list[dict],
    *,
    chunk_oversized: bool = True,
    chunk_chars: int = 500,
) -> dict:
    """Resubmit ONLY the failed documents, chunking any marked oversized."""
    raise NotImplementedError("Lab 23: implement resubmit_failed")


def choose_api(workflow: dict) -> str:
    """Return "sync" or "batch" based on latency tolerance."""
    raise NotImplementedError("Lab 23: implement choose_api")


def submission_frequency(sla_hours: float, batch_window_hours: float = 24) -> float:
    """Max hours between batch submissions to meet an end-to-end SLA."""
    raise NotImplementedError("Lab 23: implement submission_frequency")


def route_for_review(records: list[dict], *, confidence_threshold: float = 0.75) -> dict:
    """Split records into {"auto": [...], "review": [{**rec, "reasons": [...]}]}"."""
    raise NotImplementedError("Lab 23: implement route_for_review")


def accuracy_by_segment(
    records: list[dict],
    *,
    segment_field: str = "document_type",
    fields: list[str] | None = None,
) -> dict:
    """Field-level accuracy overall and per segment; expose the worst segment."""
    raise NotImplementedError("Lab 23: implement accuracy_by_segment")
