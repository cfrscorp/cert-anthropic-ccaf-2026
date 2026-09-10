# BACKLOG

Usage:
- Backlog items are numbered globally as `BL-NNN` (zero-padded, unique across all items).
- Two sections exist: **Open**, for incomplete/outstanding items; and **Completed**, for those resolved — by completion, descoping, tabling, etc. When resolving, move the item to Completed with a one-line note on how.
- Open items are generally resolved per-section, top-down (Fixes, then Changes, then Additions). This is a guideline, not a hard rule — items may be completed out of order when dependencies or priorities require it (see Sequencing).

Sequencing note: BL-001 adds a **Labs** nav entry that does not exist until BL-003 ships, so the recommended order is **BL-002 → BL-003 → BL-001** (a deliberate deviation from strict top-down).

Sequencing note: BL-026–BL-037 are one epic (question-tier restructuring, dynamic set loading, versioning, flashcard overhaul) scoped via a feedback pass — see full findings/rationale for each in the plan file used to derive them. Recommended order, since several depend on foundations landing first: **BL-027 → BL-026 → BL-028 → BL-033 → BL-030 → BL-029 → BL-032 → BL-031**, with **BL-034 → BL-035 → BL-036 → BL-037** runnable in parallel on the flashcards side.

## Open

### Fixes

- [ ] BL-032 - Quiz questions: cross-source duplicate/overlap pass across the three difficulty tiers (BL-028). Confirmed concrete near-duplicates between Standard and Intermediate already (e.g. the $500-refund-hook scenario, the verbose-skill-context-isolation scenario, the comment-accuracy-false-positive scenario, the `stop_reason` control-loop concept — 64 shared tags overall). For each overlapping cluster, delete the true duplicate or deliberately differentiate it per-tier. Run before BL-031's expansion; must also cover Hard-tier content once BL-029 lands.
- [ ] BL-034 - Flashcards: single-concept overhaul. ~1/3 to just under half of the 90 cards conflate 2-3 distinct facts onto one card (e.g. `fc-1.3-003`, `fc-4.3-003`, `fc-5.3-003`, `fc-3.6-001`, `fc-1.2-001`). Split conflated cards into clean single-concept cards; majority of cards are already fine and don't need touching. Settle a per-task-statement target count (today: flat 3/task) before authoring.

### Changes

- [ ] BL-031 - Quiz questions: expand the Intermediate tier to close 4 missing task-statement gaps (1.5, 2.2, 4.2, 5.3) and recalibrate difficulty (currently skews *easier* than Standard, not "intermediate") to reach the 50-minimum/100-preferred target. Do after BL-032's dedup pass.

### Additions

- [ ] BL-029 - Quiz questions: adopt the untracked, unreferenced `study/data/questions-lvl2.json` (90 Qs, full 30-task-statement coverage, difficulty concentrated 7-9, schema-valid) as the Hard tier's base, pending your own quality review of a larger sample and BL-032's dedup pass.
- [ ] BL-035 - Flashcards Web UI: add a task-statement filter alongside the existing domain-only select, mirroring Quiz's existing two-tier domain→task cascade (`domainOptions()`/`taskOptions()` already generic/reusable). Every flashcard already has `task_statement`; it's just not exposed as a filter yet.
- [ ] BL-036 - Flashcards: self-graded recall tracking (flip → "got it"/"missed it", Anki/Leitner-style), enabling a "review missed" mode. New history data model needed (flashcards currently have zero progress-tracking concept, unlike quiz questions) — likely mirroring `quiz.py`'s `{attempts, correct, last_result, last_seen}` shape.
- [ ] BL-037 - New Flashcards TUI (`study/tools/flashcards_tui.py`), mirroring `quiz_tui.py`'s architecture: a `flashcards.py` "core" module (data model, loading, history per BL-036, filtering) imported by a thin presentation-only TUI script. Depends on BL-036's history model being settled first.

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
- [x] BL-023 - Added `study/videos/` — one Markdown file per exam domain (D1–D5) linking 1-3 real YouTube videos per concept (55 unique links, every one verified to resolve via YouTube's oEmbed API), prioritizing Anthropic's official channel and hands-on coding demos, plus a `README.md` index.
- [x] BL-024 - Added a `videos` array (`{title, url}`) to every concept in `concepts.json`, parsed from `study/videos/domain-*.md`; extended `concepts.schema.json` to validate it. `cd study && uv run pytest` green (30 concepts, 64 video entries).
- [x] BL-025 - Concepts view: render each concept's `videos` as a "Videos" section (text links only, no thumbnails) between Code and Practice. Link text is a succinct, concept-tied label ("Video N: <concept title>"); the real video title becomes the link's `title` tooltip in place of alt text.
- [x] BL-027 - Docs: repointed `README.md`, `.claude/CLAUDE.md`, and `labs/README.md`'s broken links from the renamed `anthropic-ccaf-exam-guide-2026.md` to `anthropic-ccaf-exam-guide-2026-07.md` (verified verbatim-current against the official Sept-2026 exam guide PDF); repo-wide sweep confirmed no other stale references remain.
- [x] BL-026 - Site: version number in the footer. Added `config.app_version` (`"1.1.0"`) to `meta.json` (+ `meta.schema.json`), rendered in the footer via `app.js`'s `boot()` (hidden spans in `index.html` unhidden once `DATA.meta` loads); `study/pyproject.toml` and `study/serve.py`'s `__version__` bumped to match, with two new `test_study_data.py` tests asserting all three stay in sync. `cd study && uv run pytest` green (23 passed).
- [x] BL-028 - Quiz questions: renamed/relocated into three difficulty tiers — `study/data/questions-standard.json` (was `questions.json`, 240 Qs), `study/data/questions-intermediate.json` (was `.working/questions2.json`, 57 Qs, now a real tracked file), `study/data/questions-hard.json` (was the untracked `study/data/questions-lvl2.json`, 90 Qs — see BL-029). Updated `app.js`'s fetch (still Standard-only until BL-033's picker lands), all `quiz.py`/`quiz_tui.py` CLI examples, and `study/README.md`'s content-model table. `test_study_data.py` now schema-validates and structurally checks all three tiers combined (global ID-uniqueness, real task statements, A-D options, distractor completeness, lab links), added a 50-question-minimum-per-tier guard, and kept the 8/task coverage target scoped to Standard only (where it was calibrated). Verified end-to-end: web server serves `questions-standard.json` (240 Qs, 200 OK), and `quiz.py --list` runs clean against all three files. `cd study && uv run pytest` green (26 passed).
- [x] BL-033 - Web UI: dynamic question-set and flashcard-set picker. Added `study/data/sets.json` (+ `sets.schema.json`) manifest listing all question/flashcard sets by id/label/file; `test_study_data.py` validates it and checks it stays in sync with the files actually on disk. `app.js`'s `boot()` now eager-loads every listed set into `DATA.questionSets`/`DATA.flashcardSets`; a new "Question set"/"Flashcard set" dropdown (Quiz and Flashcards views) swaps which loaded set `DATA.questions`/`DATA.flashcards` points at, with the choice persisted in `localStorage` across reloads. Verified end-to-end with Playwright (real Chrome): switching sets updates the domain list, starting a quiz on the Hard set renders real Hard-tier content, and the selection survives a genuine page reload; flashcards set-switching verified structurally (only one flashcard set exists today). `cd study && uv run pytest` green (29 passed).
- [x] BL-030 - Quiz questions: real multi-select ("Select N") item support, across all three surfaces. Schema: `options` now allows 4-5 items (A-E), `correct` accepts a single letter or a 2+-letter array, `rationale.distractors` gained an `E` slot; `test_study_data.py`'s integrity checks now compute expected distractor/option keys from a `_correct_set()` helper so they work for either shape. `quiz.py`/`quiz_tui.py`: `prompt_answer` takes an optional `select_count`, parsing multi-letter input in any order/format ("AC", "A,C", "A C"); grading does set comparison; feedback shows the full correct set, rationale for each wrongly-chosen key, and a "Missed: X" note for any correct key not selected. `app.js`'s Quiz view renders a "Select N" pill and a Submit button (enabled only at exactly N selections) for multi-select items, toggling a new `.is-selected` option state; single-select items are completely unchanged (separate code path). Verified end-to-end (schema validation, CLI/TUI grading incl. reversed-order and invalid-input handling, and Playwright browser testing of the checkbox/submit/grading flow) using one of the real "Select TWO" questions excluded earlier this session as a temporary, non-committed test fixture — cleanly removed after. `cd study && uv run pytest` green (29 passed).

<!-- EOF -->
