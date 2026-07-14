# Lab 17 — Batch Processing Strategies

| | |
|---|---|
| **Difficulty** | 5 / 10 |
| **Estimated time** | 1:30 |
| **Prerequisites** | L04 |
| **Exam mapping** | Task Statement 4.5 |

## Objective

Learn when the **Message Batches API** is the right tool and how to operate it
correctly: build correlatable batch requests, split succeeded from failed
results, resubmit *only* the failures (with the modifications that fix them), and
do the SLA arithmetic that decides how often you must submit.

By the end you can:

- Build batch requests with a **unique `custom_id`** per document and explain why
  that id — not list position — is how you correlate a response to its source.
- Submit a batch and collect results into succeeded/failed buckets.
- Resubmit **only the failed documents** (identified by `custom_id`), chunking any
  that failed for exceeding the context limit.
- Match an API to a workflow's latency tolerance: **synchronous** for blocking
  pre-merge checks, **batch** for overnight/weekly analysis (Sample Question 11).
- Compute the **maximum submission interval** that keeps a batch pipeline inside a
  given SLA.

## Background

The Message Batches API processes a set of requests asynchronously for about
**50% less cost** than synchronous calls. The trade-off: processing takes **up to
24 hours** with **no guaranteed latency SLA** — a batch often finishes much
sooner, but you cannot rely on that.

That single property decides everything:

- **Latency-tolerant, non-blocking work → batch.** Overnight technical-debt
  reports, weekly audits, nightly test generation. Nobody is sitting waiting; a
  few hours of latency is free money.
- **Blocking work → synchronous.** A pre-merge check that a developer waits on
  before merging cannot tolerate "maybe up to 24 hours." Use the sync API even
  though it costs more.

Two more facts the exam tests:

- **Correlation is by `custom_id`.** Each request carries a `custom_id`; each
  result echoes it. Results are **not** guaranteed to return in submission order,
  so you always join on `custom_id`, never on index.
- **No multi-turn tool calling in a single batch request.** A batch request
  cannot execute a tool mid-request and feed the result back. Each request must
  be a self-contained, single-shot prompt. Agentic tool loops belong on the
  synchronous API.

**Failure handling.** When some documents error (commonly for exceeding the
context limit), you resubmit **only those** — keyed by `custom_id` — after
applying a fix such as **chunking** an oversized document into smaller pieces. You
never re-run the whole batch. And before batching a large volume, you
**prompt-refine on a small sample set** to maximize first-pass success and avoid
paying for iterative resubmission.

### Submission-frequency Math

If your pipeline promises an end-to-end SLA, you must submit batches often enough
that even the *worst-placed* document lands in time. Worst case, a document
arrives just after a submission cutoff: it waits the full submission **interval**
before the next batch goes out, then up to the **batch window** (24h) to process:

```
interval + batch_window_hours <= sla_hours
interval <= sla_hours - batch_window_hours
```

So a **30-hour SLA** with a **24-hour** window means submitting at least every
**6 hours**. (A conservative team might submit every 4 hours to keep a safety
buffer — that is the value the exam guide cites — but 6h is the tight upper
bound.) If the SLA is not strictly larger than the batch window, no interval can
meet it.

## Tasks

Implement the five functions in `starter/batch.py` (same public API as
`solution/`). Inject the `client` — never construct `anthropic.Anthropic()`
inside a function — so tests run offline against `MockAnthropic`.

1. **`build_requests(documents) -> list[dict]`** — one request per document of the
   shape `{"custom_id": <doc id>, "params": {...}}` with `params` carrying
   `model`, `max_tokens`, and a single user `messages` entry. Enforce **unique**
   `custom_id` (raise `ValueError` on a duplicate).

2. **`submit_and_collect(client, requests) -> dict`** — call
   `client.messages.batches.create(requests=...)` then
   `client.messages.batches.results(batch.id)`, and return
   `{"succeeded": {custom_id: message, ...}, "failed": [custom_id, ...]}`.
   Split on `item.result["type"]`; correlate by `item.custom_id`.

3. **`resubmit_failed(client, failed_ids, documents, *, chunk_oversized=True) -> dict`**
   — resend **only** the documents whose id is in `failed_ids`. Split any document
   marked `{"oversized": True}` into multiple smaller requests (unique derived
   ids) when `chunk_oversized` is True. Return the `submit_and_collect` shape.

4. **`choose_api(workflow) -> str`** — return `"sync"` or `"batch"` from the
   workflow's latency tolerance (`{"blocking": True}` or
   `{"latency_tolerance": "..."}`). Blocking/interactive → `"sync"`;
   overnight/weekly/latency-tolerant → `"batch"`.

5. **`submission_frequency(sla_hours, batch_window_hours=24) -> float`** — return
   the max hours between submissions (`sla_hours - batch_window_hours`); raise
   `ValueError` if the SLA is not strictly larger than the window.

## Deliverables

- Completed `starter/batch.py` with the same public API as `solution/`.
- All deterministic tests in `tests/test_lab17.py` passing.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-17-batch-processing
```

To compare against the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-17-batch-processing -q
```

## Stretch Goals

1. **Chunk-aware reassembly.** After chunking `doc-3` into `doc-3#chunk-0..N`,
   write a helper that stitches the per-chunk results back into one logical
   result keyed by the parent id.
2. **Cost model.** Add `estimated_savings(num_requests, sync_price)` that reports
   the ~50% batch discount, and show when resubmission churn erodes it.
3. **Sample-set refinement.** Simulate a first pass over a 5-doc sample, measure
   the first-pass success rate, and only "release" the full batch once it clears a
   threshold — the prompt-refinement-before-batching workflow.
4. **Mixed pipeline.** Given a list of workflows, route each with `choose_api` and
   report which go to batch vs sync and the blended cost.
