# L14 — Solution Notes

## Approach

`context.py` is four independent primitives that a long-running agent composes:

1. **`extract_case_facts`** — regex-scans every message and collects amounts,
   dates, order ids, and status keywords into a de-duplicated dict. This dict is
   the "case facts" block you re-inject into each prompt, *outside* the
   summarized history.
2. **`trim_tool_output`** — a dict comprehension that keeps only the requested
   top-level keys, in order, skipping any that are absent.
3. **`order_for_position`** — synthesizes a "Key Findings" section from each
   input section's one-line `summary`, puts it at index 0, then appends the
   detailed sections, each behind its `title` header.
4. **`Scratchpad` / `load_manifest`** — a JSON-file-backed key/value store that
   flushes atomically on every `record`, plus a one-liner that loads a manifest.

See `solution/context.py` for the full implementation.

## Key decisions & why

- **Why a case-facts block instead of trusting the summary (5.1).** Progressive
  summarization is lossy in exactly the dimension that matters for support and
  finance: it turns `$45.50` into "about \$45" and `2026-06-22` into "recently".
  Those approximations are worthless for issuing a refund or checking a policy
  window. By extracting the transactional facts verbatim into a structured block
  and re-injecting it every turn, the precise values live *outside* the part of
  context that gets condensed, so they never blur. Keeping them structured (four
  typed lists) also makes them cheap to render and easy for a downstream agent to
  consume — which is the "return structured data instead of verbose content"
  guidance from 5.1.

- **Why trim tool output at the source (5.1).** A 40+ field order lookup costs
  tokens on every subsequent turn it sits in history, and 35 of those fields are
  irrelevant to a return. Trimming to the ~5 relevant fields *before* the result
  enters context stops the slow token bleed that pushes real information toward
  the lossy middle of the window. The fixture (`sample_order_lookup.json`) has 47
  top-level fields on purpose.

- **Why summary-first with headers (lost in the middle) (5.1).** Models attend
  reliably to the start and end of a long input and drop content from the middle.
  If you concatenate ten detailed sections and hope the model synthesizes them,
  the middle ones effectively vanish. Placing a compact key-findings summary at
  index 0 guarantees the conclusions land in the high-attention region, and giving
  every detail section an explicit header lets the model (and a human) navigate to
  specifics instead of scanning prose. `order_for_position` enforces both.

- **Why flush the scratchpad on every write (5.4).** Context degrades in long
  sessions — the model starts answering from "typical patterns" rather than the
  specific facts it discovered earlier. A scratchpad file is the durable
  counter-store: write the finding once, recall it later regardless of what the
  context window has done. Flushing on *every* `record` (atomically, via a temp
  file + `os.replace`) makes it crash-recoverable — a fresh process, or the same
  coordinator after a restart, reads the file and picks up where it left off. A
  manifest is the same idea at the multi-agent level: each agent exports state to
  a known path and the coordinator `load_manifest`s them on resume.

- **Why atomic writes.** A naive `open(path, "w")` that crashes mid-write leaves
  a truncated, unparseable JSON file — the worst outcome for a crash-recovery
  mechanism. Writing to a temp file and `os.replace`-ing it makes the update
  all-or-nothing.

## Reference walkthrough

Using `sample_conversation.json`:

| Category | Extracted (verbatim) |
|---|---|
| amounts | `$129.99`, `$45.50` |
| dates | `2026-06-15`, `2026-06-20`, `2026-07-05`, `2026-06-22` |
| order_numbers | `A-10432`, `ORD-77219` |
| statuses | `in transit`, `delivered`, `refund` |

The order-id regex `\b[A-Z]{1,4}-\d{3,}\b` matches `A-10432` inside `#A-10432`
(the `#` is not captured) and `ORD-77219`. Status matching walks a vocabulary
with longer phrases first (`out for delivery` before `delivered`) and de-dupes,
so `delivered` appears once even though two turns mention it.

`trim_tool_output(order, ["order_id","status","order_total","customer_email",
"return_eligible"])` returns exactly those five keys out of 47; `internal_notes`,
the full billing/shipping addresses, and `line_items` are dropped.

`order_for_position([...])` returns `[{"header":"Key Findings", ...}, {"header":
"Order A-10432", ...}, {"header":"Order ORD-77219", ...}]` — summary at index 0,
details after, every element headed.

`Scratchpad(path).record("refund_amount","$45.50")` writes the JSON file; a fresh
`Scratchpad(path).recall("refund_amount")` returns `"$45.50"` because `__init__`
reloads the file from disk.

## Common mistakes

- **Summarizing the numbers instead of extracting them.** The whole point is to
  keep `$45.50` and `2026-06-22` exact. If your extractor rounds, normalizes, or
  paraphrases, you've reintroduced the bug.
- **Including the `#` in the order id.** `#A-10432` — the id is `A-10432`.
- **Letting `delivered` also match a `delivery`-based phrase**, or emitting
  duplicates. Order the vocabulary longest-first and de-dupe.
- **Raising when a requested field is missing** in `trim_tool_output`. Skip it so
  callers can pass a stable field set across heterogeneous tool results.
- **Putting details before the summary**, or dropping section headers — that
  recreates the lost-in-the-middle problem the function exists to fix.
- **Only writing the scratchpad on close / in `__del__`.** A crash then loses
  everything. Flush on every `record`.
- **Non-atomic writes** that can leave a half-written JSON file.
- **`recall` reading only in-memory state written by the *same* instance.** A
  fresh instance must reload from disk in `__init__`.

## Checklist

- [ ] `extract_case_facts` returns `amounts`, `dates`, `order_numbers`,
      `statuses`, each de-duped and verbatim.
- [ ] Order ids exclude the `#`; statuses come from a known vocabulary.
- [ ] `trim_tool_output` returns only requested keys, in order, skipping absent.
- [ ] `order_for_position` puts the summary at index 0 and headers every section.
- [ ] `Scratchpad.record` flushes to disk (atomically); a fresh instance recalls.
- [ ] `load_manifest` round-trips a JSON manifest dict.
- [ ] `LAB_TARGET=solution uv run pytest lab-14-context-management` is green.
