# Canonical review scenario — the 14-file stock-tracking PR

This is the Sample Question 12 situation, used as the canonical case throughout
the lab. Read it before implementing `plan_review_passes` — the tests use the
same 14 files.

## The pull request

A pull request modifies **14 files** across the stock-tracking module:

| # | File | What changed |
|---|------|--------------|
| 1 | `inventory.py` | Core on-hand quantity tracking |
| 2 | `stock_levels.py` | Min/max level calculations |
| 3 | `reorder.py` | Restock threshold + reorder trigger |
| 4 | `warehouse.py` | Per-warehouse allocation |
| 5 | `sku_catalog.py` | SKU lookup + metadata |
| 6 | `transfers.py` | Inter-warehouse transfers |
| 7 | `suppliers.py` | Supplier records |
| 8 | `purchase_orders.py` | PO creation from reorder events |
| 9 | `stock_events.py` | Event log for stock movements |
| 10 | `valuation.py` | Inventory valuation (FIFO/average cost) |
| 11 | `api/stock_routes.py` | HTTP endpoints for stock queries |
| 12 | `api/schemas.py` | Request/response schemas |
| 13 | `db/models.py` | ORM models + migrations |
| 14 | `tests/test_stock.py` | Test updates |

## The symptom (single-pass review)

A single review pass that analyzes **all 14 files together** produces:

- **Inconsistent depth** — detailed feedback on some files, superficial comments
  on others.
- **Missed bugs** — obvious local issues slip through because attention is spread
  across 14 files at once (attention dilution).
- **Contradictory feedback** — the same pattern is flagged as problematic in one
  file and approved in another *within the same PR*.

## Why the tempting fixes are wrong (Sample Question 12)

- **Bigger model / larger context window** — does not fix *attention quality*.
  The model can hold 14 files in context and still spread attention thinly. The
  problem is not capacity; it is focus.
- **Force developers to split into 3–4 file PRs** — shifts the burden onto
  developers without improving the review system, and fragments cross-file
  review.
- **Consensus of 3 full-PR runs (flag only issues seen in ≥2 runs)** — actively
  *suppresses* real bugs. Subtle issues are caught intermittently; requiring
  agreement across runs discards exactly the low-frequency findings you most want.

## The fix — multi-pass decomposition (Task Statements 1.6 + 4.6)

Split the review into focused passes:

1. **14 local passes** — one per file. Each pass sees a single file and looks for
   local issues (bugs, edge cases, error handling). Consistent depth, no
   dilution.
2. **1 integration pass** — a single cross-file pass over all 14 files that looks
   for data-flow issues, interface/contract mismatches, and contradictions the
   per-file passes structurally cannot see (e.g. `reorder.py` triggering a PO
   that `purchase_orders.py` builds with the wrong quantity field).

That is **15 passes total** — `plan_review_passes(PR_FILES)` returns exactly this
structure (14 `local` + 1 `integration`).

## Independence matters too (Task Statement 4.6)

If Claude *generated* part of this PR, the same session reviewing its own code is
a **self-review**: it retains the reasoning it used while writing, so it is less
likely to question its own decisions. Run each pass with an **independent
instance** that never saw the generation reasoning — that is what
`is_independent_review` and `independent_second_pass` model. Finally, have each
finding self-report a confidence so `route_by_confidence` can send high-confidence
findings to auto-apply and everything else to human review.
