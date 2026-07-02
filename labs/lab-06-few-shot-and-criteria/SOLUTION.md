# Lab 06 — Solution notes

## Approach

Encode the two Domain 4 techniques as a small, testable `prompt_builder.py`:

- **Explicit categorical criteria (4.1)** live in the *structure* of the prompt —
  a REPORT list built from the caller's `criteria`, a concrete SKIP list, and a
  severity rubric with real code examples. `has_explicit_criteria` and
  `is_vague_instruction` are the guards that keep prompts on the categorical side
  of the line.
- **Few-shot examples (4.2)** are rendered verbatim, each showing input, output,
  and the *why* — the reason the chosen action beats a plausible alternative. That
  reasoning is what lets the model generalize instead of memorizing your cases.

Everything here is pure string work, so no Claude client is needed; the optional
`@pytest.mark.llm` test grades a *built* prompt with the shared `grade` helper.

## Key decisions & why

- **`criteria` is the REPORT list; SKIP is concrete and built-in.** The whole
  point of 4.1 is a categorical rule, so the prompt always pairs "REPORT only
  when …" with a named "SKIP (do NOT report) …" list. Leaving SKIP to the model
  ("be conservative") is exactly the anti-pattern.
- **Precision-over-recall framing at the top.** The prompt states that a false
  positive erodes trust in *every* category and instructs "when unsure, SKIP" —
  the guide's core 4.1 insight, and the opposite of a low-confidence guess.
- **Severity rubric carries distinct code examples.** Adjectives ("important",
  "minor") classify inconsistently; a concrete snippet per level (SQL injection →
  critical, `sum/len` on an empty list → high, unbounded cache → medium, `== True`
  → low) makes the boundary reproducible. The test enforces that the examples are
  distinct, catching copy-paste placeholders.
- **`has_explicit_criteria` = inclusion directive AND exclusion directive** (or a
  ≥2-level severity rubric plus a report directive). This is what separates
  categorical criteria from vague hedges: a vague prompt names *confidence*, never
  categories to *exclude*, so it lacks the exclusion directive and returns False.
- **`is_vague_instruction` is phrase-pattern based.** It flags the canonical
  offenders from the guide ("be conservative", "only … high-confidence", "use your
  judgment", "when in doubt", "check that … are accurate") while leaving concrete
  categorical instructions alone.
- **`build_review_prompt` validates 2-4 examples.** The guide is specific: 2-4
  targeted examples. Fewer than two isn't "few-shot"; more than four is usually
  token bloat for this task. Each example must have `input`/`output`/`why`, so a
  malformed example fails loudly instead of silently dropping the reasoning.

## Reference walkthrough

1. `is_vague_instruction(text)` → lower-case, return True if any vague regex
   matches.
2. `has_explicit_criteria(prompt)` → compute `has_inclusion` (report/flag/raise),
   `has_exclusion` (skip/ignore/exclude/"do not report"), and the set of distinct
   severity labels; return True if inclusion+exclusion, or inclusion + ≥2
   severities.
3. `severity_rubric()` → dict of `critical/high/medium/low`, each with
   `definition`, a distinct `code_example`, and an `action`.
4. `build_review_prompt(criteria, few_shot)`:
   - validate `criteria` non-empty and `2 <= len(few_shot) <= 4`;
   - render the REPORT list from `criteria`, the fixed SKIP list, the output
     fields, and the severity block from `severity_rubric()`;
   - render each example via a helper that requires `input`/`output`/`why`;
   - return the assembled prompt (which `has_explicit_criteria` then accepts).

## Common mistakes

- **Confidence filtering instead of categories.** "Only report high-confidence
  findings" does not improve precision — it just shifts the guessing. Name the
  categories to report and to skip.
- **A severity rubric of adjectives.** Without a concrete code example per level,
  the same defect gets rated differently across runs.
- **Few-shot examples with no reasoning.** For ambiguous cases, omitting the *why*
  removes the part that lets the model generalize; it will only match your literal
  inputs.
- **One example (or ten).** The guide says 2-4. `build_review_prompt` enforces it.
- **Letting the vague-prompt test pass on the starter.** `NotImplementedError`
  subclasses `RuntimeError`, so a `pytest.raises(RuntimeError)` guard would pass
  vacuously against an unfinished starter. The tests instead call the functions
  and assert on real return values, so the starter fails on the real assertions.
- **Dropping attribution in extraction.** Recording a raw `[3]` marker instead of
  resolving it to its bibliography entry loses the source — the extraction
  examples demonstrate the correct join.

## Checklist

- [ ] `is_vague_instruction` flags "be conservative", "only high-confidence …",
      "use your best judgment", "when in doubt"; False for concrete criteria.
- [ ] `has_explicit_criteria` True for a REPORT+SKIP prompt; False for a vague one.
- [ ] `severity_rubric` returns ≥3 levels, each with a distinct concrete
      `code_example`.
- [ ] `build_review_prompt` embeds every criterion and every example (input,
      output, why); rejects empty criteria and non-2-4 example counts.
- [ ] `has_explicit_criteria(build_review_prompt(...))` is True.
- [ ] `LAB_TARGET=solution uv run pytest lab-06-few-shot-and-criteria -q` is green.
