# Lab 17 — Solution notes

## Approach

One module, `batch.py`, with five small functions that map to the four skills in
Task Statement 4.5: build correlatable requests, collect results, handle failures
by resubmitting only what failed (with a fix), match the API to the workflow, and
do the SLA arithmetic. Every Claude-touching function takes an injected `client`
so the whole thing runs offline against `MockAnthropic(batch_handler=...)`.

## Key decisions & why

- **`custom_id` is the join key, not list position.** `build_requests` stamps a
  unique `custom_id` per document and raises on a collision; `submit_and_collect`
  buckets results by `item.custom_id`. Batch results are not guaranteed to return
  in submission order, so joining on position would silently mis-attribute
  outputs. The unique-id guard turns a subtle data-corruption bug into a loud
  error at build time.

- **Split succeeded/failed on `item.result["type"]`.** The mock (and the real
  API) mark each result `"succeeded"` or `"errored"`. Succeeded results go into a
  `{custom_id: message}` map; errored ids go into a `failed` list you can feed
  straight back into `resubmit_failed`.

- **Resubmit only failures, and modify before resending.** `resubmit_failed`
  selects documents by `custom_id` from `failed_ids` — it never re-runs the whole
  batch. Documents flagged `oversized` are chunked into smaller requests with
  derived unique ids (`doc-3#chunk-0`, ...) so an over-context failure actually
  gets fixed on the retry instead of failing again. Chunking is toggleable
  (`chunk_oversized`) so the function also covers "resend as-is" retries.

- **`choose_api` encodes the Sample Q11 split.** Anything blocking on the result
  (a merge gate, an interactive request) returns `"sync"`; latency-tolerant work
  (overnight, weekly) returns `"batch"`. A workflow with no latency signal raises
  rather than guessing.

- **`submission_frequency` returns the tight worst-case bound.** `interval =
  sla_hours - batch_window_hours`. The worst-placed document waits a full
  interval for the next submission, then the full window to process; the sum must
  fit the SLA. An SLA not larger than the window can't be met, so it raises.

### Why the Sample Question 11 distractors are wrong

Sample Q11 proposes moving both a **blocking pre-merge check** and an **overnight
technical-debt report** to the batch API for the 50% savings. The correct answer
(A) is: batch the overnight report, keep the pre-merge check synchronous.

- **B — "switch both, poll for completion" is wrong.** Polling doesn't change the
  contract: there's no latency SLA, so a poll loop is just "poll and hope it's
  fast." A blocking pre-merge gate can't be built on hope — some batch could take
  hours and developers would be stuck.
- **D — "switch both, timeout fallback to real-time" is wrong.** The fallback
  means you often pay for the batch *and* the sync call, and you've added a whole
  timeout/retry machine to a problem the simple answer already solves. Complexity
  for no gain — just use sync for the blocking case.
- **C — "keep both synchronous to avoid ordering issues" is wrong.** Result
  ordering is a non-issue: `custom_id` correlates responses regardless of order.
  Keeping the overnight report synchronous throws away the 50% savings for a
  problem that doesn't exist.

The lesson the exam rewards: **match each API to its workflow's latency
tolerance** instead of forcing one API onto both, or bolting complexity onto the
wrong one.

## Reference walkthrough

1. `build_requests(documents)` → for each doc, `custom_id = str(doc["id"])`
   (raise on duplicate), `params = {model, max_tokens, messages=[user text]}`.
2. `submit_and_collect(client, requests)` → `create(requests=...)`,
   `results(batch.id)`, then bucket: `type == "succeeded"` →
   `succeeded[custom_id] = result["message"]`, else append to `failed`.
3. `resubmit_failed(client, failed_ids, documents, *, chunk_oversized=True)` →
   index docs by id; for each failed id, chunk if oversized else resend as-is;
   `build_requests(subset)` then `submit_and_collect`.
4. `choose_api(workflow)` → `blocking is True` or a sync tolerance string →
   `"sync"`; otherwise `"batch"`; no signal → `ValueError`.
5. `submission_frequency(sla_hours, batch_window_hours=24)` →
   `sla_hours - batch_window_hours`, guarded to be positive.

## Common mistakes

- **Correlating by position.** Zipping results with the request list assumes
  order the API doesn't promise. Always join on `custom_id`.
- **Duplicate `custom_id`s.** Two docs sharing an id means one result overwrites
  the other. Enforce uniqueness at build time.
- **Resubmitting the whole batch.** You only pay to re-run the failures. Filter
  by `failed_ids` first.
- **Resubmitting oversized docs unchanged.** They'll just fail again. Chunk (or
  otherwise shrink) before the retry.
- **Batching a blocking workflow.** No latency SLA means a pre-merge gate can
  stall for hours. Blocking → sync, always.
- **Expecting multi-turn tool use in one batch request.** A batch request is
  single-shot; it can't run a tool and continue. Use the sync API for tool loops.
- **Off-by-window SLA math.** Forgetting to subtract the batch window (using
  `sla_hours` directly as the interval) blows the SLA for worst-placed docs.

## Checklist

- [ ] `build_requests` emits one request per doc with a unique `custom_id` and
      well-formed `params` (model, max_tokens, user message).
- [ ] `submit_and_collect` returns `{"succeeded": {...}, "failed": [...]}` split
      by `item.result["type"]`, correlated by `custom_id`.
- [ ] `resubmit_failed` resends only `failed_ids`; chunks oversized docs into
      multiple unique-id requests; can disable chunking.
- [ ] `choose_api` → `"sync"` for blocking, `"batch"` for overnight/weekly;
      raises on no signal.
- [ ] `submission_frequency(30, 24) == 6`; raises when SLA ≤ window.
- [ ] `LAB_TARGET=solution uv run pytest lab-17-batch-processing -q` is green.
