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
- [x] BL-004 - Flashcards: "Reveal Answer" / "Flip Back" restyled as a clay button (was a faint text link).
- [x] BL-005 - Header: black asterisk logo on the orange brand mark.
- [x] BL-006 - Concepts: syntax highlighting for all code samples (dependency-free tokenizer; theme-aware token colors).
- [x] BL-007 - serve.py: honor an explicit `--port` and fix the silent random-port fallback (probe socket lacked `SO_REUSEADDR`); clear error + Windows excluded-range hint when a port can't bind.
- [x] BL-008 - Mobile — Site nav: tightened horizontal spacing so the tabs fit one line instead of spreading/wrapping.
- [x] BL-009 - Mobile — Filter dropdowns (Flashcards/Concepts/Quiz): Domain/Task/Length selects go full-width with consistent card padding (no odd wrap/right-edge gap).
- [x] BL-010 - Mobile — Flashcards: fixed "Reveal Answer"/"Flip Back" overlapping card text; the card now auto-grows to fit long answers (grid-stacked faces).
- [x] BL-011 - Mobile — Quiz: Task Statement select no longer runs outside its card (selects capped to `max-width:100%`).
- [x] BL-012 - README: add a home-page screenshot (`docs/study-app.png`) at the top.
- [x] BL-013 - README: add a "By the Numbers" promo section (240 questions / 90 flashcards / 30 concepts / 25 labs) before Study Materials.
- [x] BL-014 - README: title-case all headings; rename "What's here" → "Study Materials" and "The lab program at a glance" → "Labs At A Glance".
- [x] BL-015 - Title Case for all headings in the remaining READMEs (labs/README.md, labs/_shared/README.md, study/README.md, 25 lab READMEs) via a script that skips code fences and preserves acronyms/code spans/filenames.
- [x] BL-016 - study/README.md: added an "Install uv" quick start (macOS + Windows best-practice install) just before "Run It", linking the uv install guide.
- [x] BL-017 - README (root): added a concise uv install line (macOS/Linux + Windows one-liners + link) under Quick Start.
- [x] BL-018 - Concepts: "Expand All" / "Collapse All" buttons in the filter bar (toggle every concept's `<details>`; work after any domain filter).
- [x] BL-019 - Concepts: inline search box (beside Expand/Collapse) that live-filters concepts by task statement, title, and body text; hides empty domain sections and shows a no-results note.
- [x] BL-020 - Concepts: aligned the filter controls by removing the "Domain" label (bare, aria-labelled select) so the dropdown lines up with the search box and buttons.
- [x] BL-021 - Concepts: highlight search matches in place via the CSS Custom Highlight API (`::highlight(concept-search)`, amber `--hl-bg` in both themes) — no DOM mutation, so it never disturbs code spans; expand/collapse stays manual (highlights in a collapsed body appear once the user expands it).
- [x] BL-022 - Followed up on BL-021: a search match hidden inside a collapsed body was invisible even though highlighted (nothing expands by default), so search now auto-reveals only the concepts it matches, tracking what it opened so a manual Expand All / Collapse All choice is never overridden.
- [x] BL-023 - Added `study/video/` — one Markdown file per exam domain (D1–D5) linking 1-3 real YouTube videos per concept (55 unique links, every one verified to resolve via YouTube's oEmbed API), prioritizing Anthropic's official channel and hands-on coding demos, plus a `README.md` index.

<!-- EOF -->
