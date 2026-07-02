"""Batch processing strategies with the Message Batches API (Lab 17 — SOLUTION).

Public API (must match starter/):

    build_requests(documents) -> list[dict]
    submit_and_collect(client, requests) -> dict
    resubmit_failed(client, failed_ids, documents, *, chunk_oversized=True) -> dict
    choose_api(workflow) -> str            # "batch" | "sync"
    submission_frequency(sla_hours, batch_window_hours=24) -> float

The Message Batches API trades latency for cost: ~50% cheaper, but processing
takes up to 24 hours with NO guaranteed latency SLA. Use it for non-blocking,
latency-tolerant work (overnight reports, weekly audits); never for blocking
workflows (pre-merge checks) where a human is waiting on the result.

A batch also cannot run multi-turn tool calling inside a single request — it
cannot execute a tool mid-request and feed the result back — so batch requests
must be self-contained single-shot prompts.

Callers inject the Anthropic client (real SDK or MockAnthropic) so tests run
offline. Do not construct a client inside these functions.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "build_requests",
    "submit_and_collect",
    "resubmit_failed",
    "choose_api",
    "submission_frequency",
]

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024

# Latency-tolerance descriptors that require the *synchronous* API because a
# caller (human or CI gate) is blocked waiting on the answer.
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


def _params_for(text: str) -> dict[str, Any]:
    """Build the single-shot request params for one document's text."""
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": text}],
    }


def build_requests(documents: list[dict]) -> list[dict]:
    """Turn documents into Message Batches requests with a unique custom_id each.

    Each document is a dict with at least an ``"id"`` and ``"text"``. The
    returned requests have the shape the API expects::

        {"custom_id": <doc id>, "params": {"model", "max_tokens", "messages"}}

    ``custom_id`` is what correlates each response back to its source document,
    so it MUST be unique across the batch — a collision is raised loudly rather
    than silently dropping a result.
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

        {
          "succeeded": {custom_id: message, ...},   # the model output per doc
          "failed":    [custom_id, ...],            # errored requests
        }

    Correlation is entirely by ``custom_id`` — batch results are NOT guaranteed
    to come back in submission order, so never index by position.
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
    """Split an oversized document's text into <=chunk_chars pieces.

    Each chunk becomes its own document with a derived, still-unique id so the
    chunks can be correlated back to the parent (``<id>#chunk-0`` ...).
    """
    text = doc["text"]
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    pieces = [text[i : i + chunk_chars] for i in range(0, len(text), chunk_chars)] or [""]
    return [
        {"id": f"{doc['id']}#chunk-{n}", "text": piece}
        for n, piece in enumerate(pieces)
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

    You never resubmit the whole batch — you resend just the documents whose
    ``custom_id`` errored, optionally applying the modification that fixes the
    failure. The common fix is chunking a document that exceeded the context
    limit: a document flagged ``{"oversized": True}`` is split into multiple
    smaller requests before resubmission.

    Returns the same shape as :func:`submit_and_collect`.
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

    requests = build_requests(to_send)
    return submit_and_collect(client, requests)


def choose_api(workflow: dict) -> str:
    """Return "sync" or "batch" for a workflow based on latency tolerance.

    A workflow is a dict describing how the result is consumed. Signals::

        {"blocking": True}                      -> "sync"   (someone is waiting)
        {"latency_tolerance": "blocking"}       -> "sync"
        {"latency_tolerance": "overnight"}      -> "batch"
        {"latency_tolerance": "weekly"}         -> "batch"

    Rule: if anything blocks on the result (a developer at a merge gate, an
    interactive request), use the synchronous API — the batch window (up to 24h,
    no SLA) is unacceptable. Otherwise the work is latency-tolerant and the batch
    API's ~50% savings apply. This is exactly the Sample Question 11 split:
    pre-merge check -> sync, overnight technical-debt report -> batch.
    """
    if workflow.get("blocking") is True:
        return "sync"
    tolerance = str(workflow.get("latency_tolerance", "")).strip().lower()
    if not tolerance and "blocking" not in workflow:
        raise ValueError(
            "workflow needs a 'blocking' bool or a 'latency_tolerance' string"
        )
    if tolerance in SYNC_TOLERANCES:
        return "sync"
    return "batch"


def submission_frequency(sla_hours: float, batch_window_hours: float = 24) -> float:
    """Max hours between batch submissions to meet an end-to-end SLA.

    Worst case, a document arrives just after a submission cutoff: it waits the
    full submission ``interval`` before the next batch goes out, then up to
    ``batch_window_hours`` to process. To stay within the SLA::

        interval + batch_window_hours <= sla_hours
        interval <= sla_hours - batch_window_hours

    So a 30h SLA with a 24h window means submitting at least every 6h. If the
    SLA is not strictly larger than the batch window it cannot be met at all
    (there is no positive interval), so that is raised as an error.
    """
    interval = float(sla_hours) - float(batch_window_hours)
    if interval <= 0:
        raise ValueError(
            f"SLA of {sla_hours}h cannot be met with a {batch_window_hours}h "
            "batch window (need sla_hours > batch_window_hours)"
        )
    return interval
