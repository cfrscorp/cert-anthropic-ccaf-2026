# Lab 16 — Reference Solution

## Approach

Four small pure functions plus one optional client-driven helper encode Task
Statements 1.6 and 4.6:

1. `choose_decomposition` — a layered decision (explicit flag → known type →
   keyword signals → bounded-file-list tie-break) that returns `"prompt_chaining"`
   or `"dynamic"`.
2. `plan_review_passes` — builds N `local` passes + 1 `integration` pass.
3. `is_independent_review` — decides self-review vs fresh instance from the review
   context.
4. `route_by_confidence` — partitions findings into `auto` vs `human_review`.
5. `independent_second_pass` — drives an injected `client` to produce structured
   findings from a fresh (independent) review instance.

## Key decisions & why

**Per-file passes + one integration pass beats the alternatives (Sample Q12).**
This is the crux of the lab. A single pass over 14 files dilutes attention:
inconsistent depth, missed bugs, contradictory findings. The winning fix splits
the work so each local pass sees exactly one file (consistent depth) and a single
integration pass owns cross-file data flow. The distractors all lose for concrete
reasons:

- **Bigger model / larger context window** — capacity is not the problem;
  *attention quality* is. All 14 files already fit; adding more room does not make
  the model attend to each file evenly.
- **Force smaller PRs (3–4 files)** — shifts the burden onto developers and
  fragments the cross-file view; it does not improve the review system itself.
- **Consensus of 3 full-PR runs** — requiring an issue to appear in ≥2 runs
  *suppresses* the subtle, intermittently-caught bugs that are the whole point of
  reviewing. It optimizes for agreement, not recall.

`plan_review_passes` encodes the winning structure directly: `local` passes carry
`files == [self]`; the final `integration` pass carries `scope == "cross_file"`
and `files == all`. Exactly **one** integration pass — more would re-introduce the
contradiction problem the split was meant to solve.

**Independent review beats self-review (4.6).** A model retains the reasoning
context it used while generating code, so in the same session it tends to
rationalize rather than question its own decisions. An independent instance starts
without that reasoning and is measurably better at catching subtle issues than
"please review your own work" instructions or extended thinking.
`is_independent_review` treats *same session* or *shared reasoning context* (even
a fresh session handed the generation trace) as **not** independent, and only a
genuinely fresh instance as independent. `independent_second_pass` operationalizes
it: the caller injects a `client` that carries none of the generator's history,
and the prompt explicitly frames the reviewer as someone who "did not write this
code."

**The decomposition choice is about knowability, not size (1.6).** The deciding
question for `choose_decomposition` is *can you enumerate the subtasks up front?*
A 14-file review can (analyze each file, then integrate) → **prompt chaining**.
"Add comprehensive tests to a legacy codebase" cannot: you must map structure,
find high-impact areas, and let the plan adapt as dependencies surface →
**dynamic**. The implementation checks an explicit `open_ended` flag first, then a
known `type`, then keyword signals, and finally treats a bounded known file list
as a predictable pipeline.

**Confidence routing fails safe (4.6 / 5.5).** `route_by_confidence` sends
findings at/above the threshold to `auto` and everything else — including findings
with **no** confidence value — to `human_review`. Missing confidence is treated as
low confidence on purpose, so unlabeled findings never silently auto-apply.

## Reference walkthrough

- **`choose_decomposition`** — returns early on `open_ended` (`True → dynamic`,
  `False → prompt_chaining`); dispatches on `type`/`kind` against two frozensets;
  otherwise scores dynamic vs chaining keywords over the free-text fields; ties
  fall back to prompt chaining when a known `files` list is present, else dynamic.
- **`plan_review_passes`** — validates non-empty input, emits one `local` dict per
  file (1-indexed `pass`, `files == [name]`), then appends the single
  `integration` dict (`scope == "cross_file"`, `files == all`).
- **`is_independent_review`** — precedence: explicit `shares_reasoning_context` →
  session-id comparison → `includes_generation_reasoning`. Returns `not shares`.
- **`route_by_confidence`** — iterates once; numeric `confidence >= threshold`
  goes to `auto`, all else to `human_review`; returns both lists plus the
  threshold used.
- **`independent_second_pass`** — calls `client.messages.create` with a
  `report_finding` tool and `tool_choice={"type": "any"}`, then parses
  `report_finding` tool-use blocks into finding dicts. The mock test scripts one
  finding and asserts it surfaces, routes to `auto`, and that the request forced
  structured output.

## Common mistakes

- **Two integration passes (or per-file-pair passes).** The split calls for
  exactly one cross-file pass; extra integration passes re-create the
  contradictory-findings problem.
- **Choosing "bigger model" for the 14-file review.** Larger context does not fix
  attention dilution — the classic Sample Q12 trap.
- **Treating a fresh session as independent even when handed the generation
  trace.** If the reviewer is given the generator's reasoning, it is effectively a
  self-review; `includes_generation_reasoning` must pull it back to `False`.
- **Auto-applying findings with missing confidence.** Absent confidence must route
  to human review, not auto.
- **Deciding decomposition by task size instead of knowability.** A large but
  predictable review is still prompt chaining; a small but open-ended
  investigation is still dynamic.
- **Constructing `anthropic.Anthropic()` inside `independent_second_pass`.** The
  client must be injected so tests can pass a mock (and so the reviewer is
  genuinely independent of the generator's session).

## Checklist

- [ ] `choose_decomposition` returns `prompt_chaining` for the predictable 14-file
      review and `dynamic` for the legacy-test task; honours `open_ended`.
- [ ] `plan_review_passes(14 files)` returns 15 passes: 14 `local` + 1
      `integration`; local passes each cover one file; integration is last and
      spans all files.
- [ ] `is_independent_review` is `False` for same-session / shared-context and
      `True` for a fresh instance.
- [ ] `route_by_confidence` puts at/above-threshold in `auto`, below and
      missing-confidence in `human_review`.
- [ ] The MockAnthropic test shows an independent instance returning a missed
      finding that routes to `auto`.
- [ ] `LAB_TARGET=solution uv run pytest lab-16-decomposition-and-review` is green;
      the default (starter) run fails until the functions are implemented.
