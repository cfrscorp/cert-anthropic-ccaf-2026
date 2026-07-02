"""Batch extraction + human-review routing + accuracy reporting (Lab 23 — SOLUTION).

Public API (identical in starter/ and solution/):

    build_requests(documents) -> list[dict]
    submit_and_collect(client, requests) -> dict
    resubmit_failed(client, failed_ids, documents, *, chunk_oversized=True, chunk_chars=500) -> dict
    choose_api(workflow) -> str
    submission_frequency(sla_hours, batch_window_hours=24) -> float
    route_for_review(records, *, confidence_threshold=0.75) -> dict
    accuracy_by_segment(records, *, segment_field="document_type", fields=None) -> dict

This module scales the single-document extractor of :mod:`extract` to volume and
adds the reliability layer that keeps a high-throughput pipeline trustworthy:

* **Batch processing** (4.5) — build self-contained requests keyed by ``custom_id``,
  submit, and split results into succeeded/failed *by custom_id* (batch results are
  not ordered). Resubmit ONLY the failures, chunking any that exceeded the context
  limit. Batch trades latency for ~50% cost; never use it for blocking workflows,
  and it can't do multi-turn tool calling inside a request.
* **Human-review routing** (5.5) — send low field-level confidence, flagged
  conflicts, and info-absent extractions to a human, keeping confident ones on the
  automated path so limited reviewer capacity goes where it matters.
* **Accuracy by segment** (5.5) — a high *aggregate* accuracy can hide a poor
  document type or field. Break accuracy down per segment so a bad slice is visible
  before you dial back human review.

Callers inject the Anthropic client (real SDK or MockAnthropic). Do not construct a
client inside these functions.
"""

from __future__ import annotations

from typing import Any

from schema import build_extraction_tool, missing_required_info

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

# Latency descriptors that force the *synchronous* API (someone is blocked).
SYNC_TOLERANCES = {
    "blocking",
    "pre-merge",
    "premerge",
    "realtime",
    "real-time",
    "interactive",
    "synchronous",
    "sync",
}


# --------------------------------------------------------------------------- #
# Batch submission                                                            #
# --------------------------------------------------------------------------- #
def _params_for(text: str) -> dict[str, Any]:
    """Self-contained single-shot extraction request params for one document.

    The batch API cannot run multi-turn tool calling, so each request forces the
    extraction tool and returns in one shot — no follow-up validation-retry inside
    the batch itself (that happens after collection, on failures).
    """
    tool = build_extraction_tool()
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool["name"]},
        "messages": [
            {
                "role": "user",
                "content": (
                    "Extract the billing data by calling extract_invoice.\n\n"
                    f"<document>\n{text}\n</document>"
                ),
            }
        ],
    }


def build_requests(documents: list[dict]) -> list[dict]:
    """Turn documents into Message Batches requests with a unique custom_id each.

    Each document is a dict with at least ``"id"`` and ``"text"``. ``custom_id`` is
    what correlates each response back to its source document, so it MUST be unique
    — a collision is raised loudly rather than silently dropping a result.
    """
    requests: list[dict] = []
    seen: set[str] = set()
    for doc in documents:
        custom_id = str(doc["id"])
        if custom_id in seen:
            raise ValueError(f"duplicate custom_id: {custom_id!r}")
        seen.add(custom_id)
        requests.append({"custom_id": custom_id, "params": _params_for(doc["text"])})
    return requests


def submit_and_collect(client: Any, requests: list[dict]) -> dict:
    """Submit a batch and split results into succeeded/failed by custom_id.

    Returns::

        {"succeeded": {custom_id: message, ...}, "failed": [custom_id, ...]}

    Correlation is entirely by ``custom_id`` — never index by position.
    """
    batch = client.messages.batches.create(requests=requests)
    results = client.messages.batches.results(batch.id)

    succeeded: dict[str, Any] = {}
    failed: list[str] = []
    for item in results:
        if item.result["type"] == "succeeded":
            succeeded[item.custom_id] = item.result["message"]
        else:
            failed.append(item.custom_id)
    return {"succeeded": succeeded, "failed": failed}


def _chunk_document(doc: dict, chunk_chars: int) -> list[dict]:
    """Split an oversized document into <=chunk_chars pieces with derived ids."""
    text = doc["text"]
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    pieces = [text[i : i + chunk_chars] for i in range(0, len(text), chunk_chars)] or [""]
    return [
        {"id": f"{doc['id']}#chunk-{n}", "text": piece} for n, piece in enumerate(pieces)
    ]


def resubmit_failed(
    client: Any,
    failed_ids: list[str],
    documents: list[dict],
    *,
    chunk_oversized: bool = True,
    chunk_chars: int = 500,
) -> dict:
    """Resubmit ONLY the failed documents, chunking any marked oversized.

    You never resubmit the whole batch — resend just the errored ``custom_id``
    values, applying the fix. The common fix is chunking a document that exceeded
    the context limit: a document flagged ``{"oversized": True}`` is split into
    several smaller requests before resubmission. Returns the same shape as
    :func:`submit_and_collect`.
    """
    by_id = {str(d["id"]): d for d in documents}

    to_send: list[dict] = []
    for custom_id in failed_ids:
        doc = by_id.get(str(custom_id))
        if doc is None:
            raise KeyError(f"failed id {custom_id!r} not found in documents")
        if chunk_oversized and doc.get("oversized"):
            to_send.extend(_chunk_document(doc, chunk_chars))
        else:
            to_send.append({"id": str(doc["id"]), "text": doc["text"]})

    return submit_and_collect(client, build_requests(to_send))


def choose_api(workflow: dict) -> str:
    """Return "sync" or "batch" for a workflow based on latency tolerance.

    If anything blocks on the result (a developer at a merge gate, an interactive
    request), use the synchronous API — the batch window (up to 24h, no SLA) is
    unacceptable. Otherwise the work is latency-tolerant and the batch API's ~50%
    savings apply.
    """
    if workflow.get("blocking") is True:
        return "sync"
    tolerance = str(workflow.get("latency_tolerance", "")).strip().lower()
    if not tolerance and "blocking" not in workflow:
        raise ValueError("workflow needs a 'blocking' bool or a 'latency_tolerance' string")
    return "sync" if tolerance in SYNC_TOLERANCES else "batch"


def submission_frequency(sla_hours: float, batch_window_hours: float = 24) -> float:
    """Max hours between batch submissions to meet an end-to-end SLA.

    Worst case a document arrives just after a cutoff: it waits the full submission
    ``interval`` then up to ``batch_window_hours`` to process, so
    ``interval + batch_window_hours <= sla_hours``. A 30h SLA with a 24h window
    means submitting at least every 6h. If the SLA isn't strictly larger than the
    window it cannot be met.
    """
    interval = float(sla_hours) - float(batch_window_hours)
    if interval <= 0:
        raise ValueError(
            f"SLA of {sla_hours}h cannot be met with a {batch_window_hours}h batch window"
        )
    return interval


# --------------------------------------------------------------------------- #
# Human-review routing (Task Statement 5.5)                                    #
# --------------------------------------------------------------------------- #
def route_for_review(records: list[dict], *, confidence_threshold: float = 0.75) -> dict:
    """Split extraction records into automated vs human-review queues.

    Each record::

        {
          "custom_id": "doc-1",
          "extraction": {...},                 # the extracted fields
          "field_confidence": {field: 0..1},   # model's per-field confidence
          "conflict_detected": bool,           # optional; source inconsistency
        }

    A record is routed to human review when ANY of:
      * a field's confidence is below ``confidence_threshold`` (low confidence),
      * ``conflict_detected`` is true (ambiguous/contradictory source),
      * a downstream-required field is null (info absent — can't be automated).

    Returns::

        {"auto": [record, ...], "review": [{**record, "reasons": [...]}, ...]}

    Routing on calibrated, field-level confidence — not sentiment or a single
    request-level score — is what lets a team point scarce reviewers at the
    extractions most likely to be wrong.
    """
    auto: list[dict] = []
    review: list[dict] = []

    for rec in records:
        reasons: list[str] = []

        conf = rec.get("field_confidence", {}) or {}
        low = sorted(f for f, c in conf.items() if c < confidence_threshold)
        for field in low:
            reasons.append(f"low_confidence:{field}={conf[field]}")

        if rec.get("conflict_detected"):
            reasons.append("conflict_detected")

        missing = missing_required_info(rec.get("extraction", {}) or {})
        for field in missing:
            reasons.append(f"info_absent:{field}")

        if reasons:
            review.append({**rec, "reasons": reasons})
        else:
            auto.append(rec)

    return {"auto": auto, "review": review}


# --------------------------------------------------------------------------- #
# Accuracy by segment (Task Statement 5.5)                                     #
# --------------------------------------------------------------------------- #
def accuracy_by_segment(
    records: list[dict],
    *,
    segment_field: str = "document_type",
    fields: list[str] | None = None,
) -> dict:
    """Field-level extraction accuracy, overall and broken down per segment.

    Each record::

        {"segment": "handwritten", "prediction": {...}, "label": {...}}

    Accuracy is computed field-by-field (a field is correct when prediction == label)
    across all records for the aggregate, and within each segment. When ``fields``
    is None the label's keys define which fields are scored.

    Returns::

        {
          "overall": float,
          "by_segment": {segment: accuracy, ...},
          "counts": {segment: {"correct": int, "total": int}, ...},
          "worst_segment": segment | None,
        }

    The whole point (5.5): a strong aggregate can mask a weak segment. Surfacing
    ``worst_segment`` prevents "97% overall" from hiding a document type that is
    quietly failing — validate every segment before reducing human review.
    """
    seg_correct: dict[str, int] = {}
    seg_total: dict[str, int] = {}

    for rec in records:
        segment = str(rec.get(segment_field, rec.get("segment", "unknown")))
        prediction = rec.get("prediction", {}) or {}
        label = rec.get("label", {}) or {}
        scored = fields if fields is not None else list(label.keys())

        seg_correct.setdefault(segment, 0)
        seg_total.setdefault(segment, 0)
        for field in scored:
            seg_total[segment] += 1
            if prediction.get(field) == label.get(field):
                seg_correct[segment] += 1

    by_segment: dict[str, float] = {
        seg: (seg_correct[seg] / seg_total[seg] if seg_total[seg] else 0.0)
        for seg in seg_total
    }
    total = sum(seg_total.values())
    correct = sum(seg_correct.values())
    overall = correct / total if total else 0.0
    worst = min(by_segment, key=by_segment.get) if by_segment else None

    return {
        "overall": overall,
        "by_segment": by_segment,
        "counts": {seg: {"correct": seg_correct[seg], "total": seg_total[seg]} for seg in seg_total},
        "worst_segment": worst,
    }
