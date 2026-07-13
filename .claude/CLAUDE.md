# CCAF exam-prep repository

Study materials for the **Claude Certified Architect – Foundations (CCAF)** exam.

## Layout

- `anthropic-ccaf-exam-guide-2026.md` — the exam guide (5 domains, 30 task statements, 6 scenarios). Source of truth for all content.
- `labs/` — 25 hands-on labs + a shared offline test harness (`labs/_shared/`). See `labs/README.md`.
- `study/` — a local, offline, single-user study app (practice quiz, flashcards, concept explainers, readiness dashboard). See `study/README.md`.
- `BACKLOG.md` — the running task backlog (see below).
- `README.md` — repo overview.

## BACKLOG.md — consult and keep it current

`BACKLOG.md` tracks outstanding and completed work. Read it before starting feature work, and update it as items change.

- **IDs** are global and unique: `BL-NNN` (e.g. `BL-001`).
- Two top-level sections: **Open** and **Completed**. Open is split into **Fixes → Changes → Additions**.
- Default resolution order is per-section, top-down (Fixes first, then Changes, then Additions) — a guideline, not a rule; items may be done out of order.
- When an item is resolved (done, descoped, or tabled), move it from Open to **Completed** with a note on how it was resolved.

## Working conventions

- **Study content is schema-validated JSON** under `study/data/` — the single source of truth the web app reads. Any content/schema change must keep `cd study && uv run pytest` green (schema + integrity + per-task coverage).
- **The study web app (`study/web/`) has zero runtime dependencies** and must stay fully offline (no external requests). Fonts are self-hosted via `study/tools/fetch_fonts.py`. Preserve this when adding features.
- **Labs tests** are deterministic and offline: `cd labs && uv run pytest` (reference solutions: `LAB_TARGET=solution uv run pytest`). See `labs/_shared/README.md`.
- **Runnable Python scripts** follow the user's conventions: PEP 723 inline metadata (`uv run`-able), `argparse` `-h/--help` with an Examples epilog, module-level `__version__` + `--version`.
- **Run the study app:** `uv run study/serve.py` (stdlib launcher; opens `/web/`).
- **Ground exam content in the guide**, mirroring its sample-question style (correct answer + why each distractor is wrong).
