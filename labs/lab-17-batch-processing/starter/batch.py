"""Batch processing strategies with the Message Batches API (Lab 17 — STARTER).

Implement the TODOs below. Public API (must match solution/):

    build_requests(documents) -> list[dict]
    submit_and_collect(client, requests) -> dict
    resubmit_failed(client, failed_ids, documents, *, chunk_oversized=True) -> dict
    choose_api(workflow) -> str            # "batch" | "sync"
    submission_frequency(sla_hours, batch_window_hours=24) -> float

The Message Batches API trades latency for cost: ~50% cheaper, but processing
takes up to 24 hours with NO guaranteed latency SLA. Use it for non-blocking,
latency-tolerant work (overnight reports, weekly audits); never for blocking
workflows (pre-merge checks) where a human is waiting on the result.

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


def build_requests(documents: list[dict]) -> list[dict]:
    """Turn documents into Message Batches requests, one per document.

    Each document dict has at least an ``"id"`` and ``"text"``. Return a list of
    request dicts of the shape::

        {"custom_id": <doc id>, "params": {"model", "max_tokens", "messages"}}

    ``custom_id`` correlates each response to its source document, so it MUST be
    unique across the batch — raise ValueError on a duplicate id.
    """
    # TODO: build one request per document; enforce unique custom_id.
    raise NotImplementedError("build_requests: produce batch requests with unique custom_id")


def submit_and_collect(client: Any, requests: list[dict]) -> dict:
    """Submit a batch and split its results into succeeded/failed by custom_id.

    Steps:
      1. batch = client.messages.batches.create(requests=requests)
      2. results = client.messages.batches.results(batch.id)
      3. For each result item, inspect item.result["type"] ("succeeded"/"errored")
         and correlate by item.custom_id (NOT by position — order isn't guaranteed).

    Return::

        {"succeeded": {custom_id: message, ...}, "failed": [custom_id, ...]}
    """
    # TODO: create the batch, read results, and split by custom_id.
    raise NotImplementedError("submit_and_collect: create batch, collect results by custom_id")


def resubmit_failed(
    client: Any,
    failed_ids: list[str],
    documents: list[dict],
    *,
    chunk_oversized: bool = True,
    chunk_chars: int = 500,
) -> dict:
    """Resubmit ONLY the failed documents, chunking any marked oversized.

    Do NOT resend the whole batch — resend just the documents whose custom_id is
    in ``failed_ids``. A document flagged ``{"oversized": True}`` should be split
    into multiple smaller requests (each with a unique derived id) before
    resubmitting, when ``chunk_oversized`` is True.

    Return the same shape as submit_and_collect().
    """
    # TODO: select only failed docs by id, chunk oversized ones, then
    #       build_requests + submit_and_collect on that subset.
    raise NotImplementedError("resubmit_failed: resend only failed docs, chunk oversized")


def choose_api(workflow: dict) -> str:
    """Return "sync" or "batch" for a workflow based on latency tolerance.

    Signals in the workflow dict::

        {"blocking": True}                 -> "sync"   (someone is waiting)
        {"latency_tolerance": "blocking"}  -> "sync"
        {"latency_tolerance": "overnight"} -> "batch"
        {"latency_tolerance": "weekly"}    -> "batch"

    Rule: anything that blocks on the result (a merge gate, an interactive
    request) must use the synchronous API; latency-tolerant work uses batch.
    Raise ValueError if the workflow carries no latency signal at all.
    """
    # TODO: implement the sync-vs-batch decision.
    raise NotImplementedError("choose_api: decide sync vs batch from latency tolerance")


def submission_frequency(sla_hours: float, batch_window_hours: float = 24) -> float:
    """Max hours between batch submissions to meet an end-to-end SLA.

    Worst case a document arrives just after a submission cutoff: it waits the
    full interval before the next batch, then up to ``batch_window_hours`` to
    process. So interval + batch_window_hours <= sla_hours, i.e.::

        interval <= sla_hours - batch_window_hours

    Return that max interval. Raise ValueError if the SLA is not strictly larger
    than the batch window (no positive interval can meet it).
    """
    # TODO: compute and return the max submission interval.
    raise NotImplementedError("submission_frequency: return sla_hours - batch_window_hours")
