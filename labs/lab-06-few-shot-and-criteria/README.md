# Lab 06 — Few-shot Prompting & Explicit Criteria

| | |
|---|---|
| **Exam mapping** | Task Statements 4.1 and 4.2 |
| **Difficulty** | 3 / 10 |
| **Estimated time** | 1:30 |
| **Prerequisites** | L01 |

## Objective

Turn a vague, low-trust review prompt into one that produces **consistent,
actionable output** by combining the two highest-leverage prompt-engineering
techniques in Domain 4:

- **Explicit categorical criteria** (Task Statement 4.1): say exactly which issue
  categories to **REPORT** and which to **SKIP**, instead of hedges like "be
  conservative" or "only report high-confidence findings".
- **Few-shot examples** (Task Statement 4.2): 2-4 targeted examples that
  demonstrate the exact output format and — for ambiguous cases — the *reasoning*
  for choosing one action over a plausible alternative.

By the end you can:

- Compose a review system prompt whose criteria are categorical (REPORT vs SKIP),
  not confidence-based.
- Recognize and reject vague instructions that the exam guide flags as
  insufficient.
- Write a severity rubric with **concrete code examples** per level so
  classification is consistent.
- Build few-shot examples that generalize — including data-extraction examples
  that handle varied document structures (inline citations vs bibliographies).

## Background

Two findings from Domain 4 drive this lab.

**Explicit criteria beat vague instructions (4.1).** "Check that comments are
accurate" and "be conservative" don't move precision. What works is a categorical
rule: *"flag a comment only when its claimed behavior contradicts the actual code
behavior."* This matters because **false positives erode trust across every
category** — one noisy category makes developers ignore the accurate ones too. So
you name what to report, name what to skip, and define severity with concrete code
examples rather than adjectives.

**Few-shot examples beat more instructions (4.2).** When detailed prose still
produces inconsistent output, 2-4 examples are the most effective fix. For
ambiguous cases, each example should show the reasoning for choosing one action
over a plausible alternative — that is what lets the model *generalize* judgment to
novel patterns instead of pattern-matching your exact cases. Few-shot examples are
also the go-to for reducing hallucination in extraction from varied document
structures (an inline `(Chen et al., 2021)` vs a numbered `[3]` resolved against a
bibliography).

You will build a small `prompt_builder.py` that encodes both techniques and a set
of guards that tell explicit criteria apart from vague hedges.

## Tasks

You will complete `starter/prompt_builder.py` (same public API as `solution/`).
None of these functions call Claude — they build and inspect *prompts* — so there
is no client to inject.

1. **`is_vague_instruction(text) -> bool`** — return True for the vague hedges
   Task Statement 4.1 calls out: "be conservative", "only report high-confidence
   findings", "use your best judgment", "when in doubt", etc. A concrete
   categorical instruction must return False.

2. **`severity_rubric() -> dict`** — return at least three distinct severity
   levels (e.g. `critical` / `high` / `medium` / `low`). Each level maps to a
   dict with a `definition`, a **distinct concrete `code_example`**, and an
   `action`.

3. **`has_explicit_criteria(prompt) -> bool`** — return True when a prompt states
   categorical criteria: an inclusion directive (REPORT/flag …) paired with an
   exclusion directive (SKIP/ignore/do not report …), or an explicit severity
   rubric alongside a report directive. A vague prompt must return False.

4. **`build_review_prompt(criteria, few_shot) -> str`** — compose the system
   prompt. Validate inputs (non-empty `criteria`; 2-4 examples; each example has
   `input`, `output`, `why`). Render a REPORT section from `criteria`, a concrete
   SKIP section, the output format, the severity rubric, and every few-shot
   example (input, output, and the WHY). The result must embed every criterion and
   every example, and `has_explicit_criteria` must return True for it.

The `examples/` directory ships ready-to-use few-shot sets: `review_few_shot.json`
(an ambiguous REPORT case and an ambiguous SKIP case) and
`extraction_few_shot.json` (inline-citation vs bibliography extraction). The tests
load these; feel free to study and extend them.

## Deliverables

- Completed `starter/prompt_builder.py` with the same public API as `solution/`.
- All deterministic tests in `tests/test_lab06.py` passing.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-06-few-shot-and-criteria
```

Compare against the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-06-few-shot-and-criteria -q
```

The optional semantic check (does the built prompt actually read as one that
yields consistent, actionable output?) runs only when you opt in with a key:

```bash
ANTHROPIC_API_KEY=... uv run pytest lab-06-few-shot-and-criteria -m llm
```

## Stretch Goals

1. **Report/skip pairs.** Extend `build_review_prompt` to accept structured
   criteria (each with its own REPORT vs SKIP label) instead of a flat REPORT list
   plus a fixed SKIP list.
2. **Disable a noisy category.** Add a flag that temporarily removes one REPORT
   category from the prompt (Task Statement 4.1's remedy for restoring trust while
   you fix a high-false-positive category), and assert it disappears.
3. **Extraction prompt builder.** Write a sibling `build_extraction_prompt` that
   embeds the `extraction_few_shot.json` examples and a format-normalization rule,
   then grade (with `-m llm`) whether it correctly resolves a `[4]` marker.
4. **Counter-examples.** Add a few-shot example that shows an *acceptable* pattern
   being correctly NOT reported, to further suppress false positives while
   preserving generalization.
