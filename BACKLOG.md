# BACKLOG

Usage:
- Backlog items are numbered globally as `BL-NNN` (zero-padded, unique across all items).
- Two sections exist: **Open**, for incomplete/outstanding items; and **Completed**, for those resolved — by completion, descoping, tabling, etc. When resolving, move the item to Completed with a one-line note on how.
- Open items are generally resolved per-section, top-down (Fixes, then Changes, then Additions). This is a guideline, not a hard rule — items may be completed out of order when dependencies or priorities require it (see Sequencing).

Sequencing note: BL-001 adds a **Labs** nav entry that does not exist until BL-003 ships, so the recommended order is **BL-002 → BL-003 → BL-001** (a deliberate deviation from strict top-down).

## Open

### Fixes

None.

### Changes

None.

### Additions

None.

## Completed

- [x] BL-001 - Site: Reorder navigation to Concepts, Flashcards, Labs, Quiz, Readiness. Done in `study/web/index.html`; default landing route set to `#/concepts`; active-tab logic verified.
- [x] BL-002 - Concepts: code samples. Added optional `code_samples` to `concepts.schema.json`; authored 40 guide/lab-grounded snippets across 26 of 30 concepts (skipped where code wouldn't clarify); the Concepts view renders them as styled, language-badged code blocks. `cd study && uv run pytest` green.
- [x] BL-003 - Add Labs (browsable, offline). `study/tools/build_labs.py` renders each lab `README.md`/`SOLUTION.md` to HTML at build time into `study/data/labs.json`; new Labs view lists all 25 labs and renders instructions with a "Show solution" disclosure — no browser Markdown parser, zero runtime deps. Covered by `labs.schema.json` + tests.

<!-- EOF -->
