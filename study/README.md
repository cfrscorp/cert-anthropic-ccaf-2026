# CCAF Study App

A **local, offline, single-user** study app for the Claude Certified Architect –
Foundations (CCAF) exam: a scenario **practice-question bank**, **flashcards**,
**concept explainers**, and a **readiness dashboard** that tracks your progress
over time. No cloud, no accounts, no backend — everything runs on your machine and
your progress lives in your browser.

The content is plain, schema-validated **JSON** (`data/`); the app is dependency-free
**HTML/CSS/JS** (`web/`) that reads it.

## Run it

```bash
# From the repo root — uses uv; no extra downloads (serve.py is stdlib-only):
uv run study/serve.py
```

This starts a local server and opens `http://localhost:8000/web/`. Options:

```bash
uv run study/serve.py --port 8123      # pick a port
uv run study/serve.py --no-browser     # don't auto-open
uv run study/serve.py --help
```

**Prefer a downloaded binary?** The app is just static files, so any static server
works — point it at this `study/` directory and open `/web/`:

```bash
caddy file-server --root . --listen :8000
static-web-server -d . -p 8000
miniserve . -p 8000
```

> Why a server at all? Browsers block `fetch()` of local files opened via `file://`.
> Serving over `http://localhost` fixes that and keeps the JSON as editable files.

## Features

- **Quiz** — scenario multiple-choice (the exam's format). Filter by domain / task
  statement, answer, then see the correct choice **and why each distractor is wrong**,
  with a running score and an end-of-set summary.
- **Flashcards** — click-to-flip fact recall (CLI flags, `tool_choice` values, batch
  limits, `stop_reason`, …). Filter and shuffle.
- **Concepts** — one explainer per exam task statement (1.1–5.6): the idea, why it
  matters, the common trap, and a link to the relevant hands-on lab in `../labs/`.
- **Readiness** — a cumulative dashboard: overall readiness % (weighted by the exam's
  domain weights), per-domain and per-task mastery bars, a readiness-over-time
  sparkline, and "revisit lab-NN" suggestions for weak areas.

### Progress tracking

Progress is cumulative and persists across sessions in your browser's `localStorage`
(no accounts). Because it's browser-local, a different browser/profile or clearing
site data starts fresh — use **Export** / **Import** on the Readiness view to back up
or move your progress, or **Reset** to start over.

## Content model (`data/`)

| File | What |
|------|------|
| `meta.json` | Domains + exam weights, the 30 task statements, and the task → lab map. |
| `questions.json` | Scenario multiple-choice questions (stem, 4 options, correct, per-distractor rationale, lab link). |
| `flashcards.json` | Front/back fact-recall cards. |
| `concepts.json` | One explainer per task statement. |
| `schema/*.schema.json` | JSON Schemas; every data file is validated against these. |

### Adding or editing content

Edit the JSON in `data/`, then validate:

```bash
cd study && uv run pytest
```

The tests check schema validity, integrity (valid answer keys, complete distractor
rationales, real task statements, resolvable lab links, weights summing to 100) and
coverage (question count per task statement). Coverage is gated by `PILOT_DOMAINS` in
`tests/test_study_data.py` — widen it to all five domains once every domain is authored.
