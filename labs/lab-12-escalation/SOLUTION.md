# L12 — Solution Notes

## Approach

Three pure functions, no Claude client required, so everything is deterministic
and directly unit-testable:

- **`decide(context)`** is a flat chain of guard clauses in priority order:
  explicit/reiterated human request → multiple matches → policy gap → no progress
  → out of capability → straightforward, with an `ESCALATE` safe default at the
  bottom. It reads only the structural keys; `sentiment` and
  `self_reported_confidence` are never referenced.
- **`uses_unreliable_signal(policy)`** recursively flattens the policy dict into a
  list of lowercased string tokens (keys + string values) and checks each against
  a small set of unreliable-signal roots (`sentiment`, `confidence`,
  `frustration`, `mood`, `tone`, ...).
- **`build_escalation_criteria(examples)`** emits a prompt snippet: a numbered
  criteria section that mirrors `decide`'s priority order, an explicit "do not use
  sentiment or confidence" instruction, and a worked-examples section that embeds
  each example's situation, decision, and reasoning.

See `solution/escalation.py` for the implementation.

## Key decisions & why (tie to Sample Question 3)

Sample Question 3 is the spine of this lab. An agent at 55% first-contact
resolution escalates easy cases and botches hard ones. The four options map
directly onto design choices you make here:

- **A (correct) — explicit criteria + few-shot examples.** This fixes the actual
  root cause: a *fuzzy decision boundary*. `decide` is that boundary written as
  code; `build_escalation_criteria` is the same boundary written as a prompt. Both
  make "when do I escalate vs resolve" explicit and demonstrate it on concrete
  cases — the cheapest, most reliable, most proportionate first move.

- **B (wrong) — a self-reported confidence threshold.** LLM confidence is *poorly
  calibrated*, and it is worst on exactly the hard cases: the agent in the prompt
  is already *confidently* mishandling policy-exception cases. Gating on its
  confidence would keep it doing the wrong thing. `test_decide_ignores_self_
  reported_confidence` sweeps confidence from 0.0 → 1.0 and asserts the decision
  never moves; the `high-confidence-but-policy-gap` case (0.95 confidence, still
  `ESCALATE`) and `low-confidence-but-straightforward` case (0.2 confidence, still
  `RESOLVE`) make the point concrete.

- **C (wrong) — a separate trained classifier.** Over-engineering: it needs
  labeled data and ML infrastructure *before* prompt optimization has even been
  attempted. Reach for it only after A is exhausted.

- **D (wrong) — sentiment-based auto-escalation.** Sentiment *does not correlate
  with complexity*. A furious customer often has a one-click refund; a polite one
  may need a policy exception. Escalating on negative sentiment solves a different
  problem and would escalate the very easy cases we want resolved.
  `test_decide_ignores_sentiment` flips sentiment across the spectrum and asserts
  the decision is stable; `frustrated-but-resolvable` (`RESOLVE`) is the case that
  would break under option D.

Other decisions worth calling out:

- **Explicit human request is checked first**, so nothing can pre-empt it — the
  guide is explicit that you honor it *immediately, without first investigating*.
- **Multiple matches → `ASK_CLARIFY`, not a heuristic pick.** Guessing which
  "J. Smith" is a data-integrity risk (you might refund the wrong account).
  Requesting one more identifier is the safe, guide-mandated move.
- **Policy gap ≠ complexity.** The competitor price-match case has
  `policy_status: "silent"` and escalates because the *policy* does not cover it,
  independent of how hard it "feels".
- **`ESCALATE` is the safe default.** If a case falls through every check, we hand
  off rather than guess.

## Reference walkthrough

`decide` evaluated against the labeled cases:

| Case | Decisive key | Result |
|---|---|---|
| `explicit-human-demand` | `explicit_human_request=True` (check 1) | `ESCALATE` |
| `competitor-price-match-policy-silent` | `policy_status="silent"` (check 3) | `ESCALATE` |
| `two-j-smith-matches` | `customer_matches=2` (check 2) | `ASK_CLARIFY` |
| `damaged-item-replacement-with-photo` | straightforward + covered (check 6) | `RESOLVE` |
| `frustrated-but-resolvable` | sentiment ignored; covered + routine | `RESOLVE` |
| `frustrated-and-reiterated-human-request` | `reiterated_human_request=True` (check 1) | `ESCALATE` |
| `backend-outage-no-progress` | `can_make_progress=False` (check 4) | `ESCALATE` |
| `policy-ambiguous-on-request` | `policy_status="ambiguous"` (check 3) | `ESCALATE` |
| `high-confidence-but-policy-gap` | confidence ignored; `policy_status="gap"` | `ESCALATE` |
| `low-confidence-but-straightforward` | confidence ignored; covered + routine | `RESOLVE` |

`uses_unreliable_signal`: the `sentiment-threshold` policy contains the tokens
`sentiment_score` and `self_reported_confidence`, both of which match roots →
`True`. The `explicit-criteria` policy lists only structural signals → `False`.

`build_escalation_criteria`: given two examples, the returned string contains a
criteria section (mentioning ESCALATE / ASK_CLARIFY / RESOLVE and the
"do not use sentiment/confidence" rule) followed by both examples' situation,
decision, and reason text verbatim.

## Common mistakes

- **Branching on `sentiment` or `self_reported_confidence`.** The single biggest
  trap and the one the guide targets. Two tests will fail immediately.
- **Investigating before honoring an explicit human request.** Check 1 must come
  first; do not run policy/identity checks ahead of it.
- **Heuristically picking one of several customer matches** instead of returning
  `ASK_CLARIFY`.
- **Treating a policy gap as "just a hard case"** and trying to `RESOLVE` it. A
  gap/silent/ambiguous policy is an escalation trigger in its own right.
- **Escalating the frustrated-but-resolvable customer** because they sound upset.
  Acknowledge the frustration, but resolve; escalate only if they *reiterate* the
  request for a human.
- **`uses_unreliable_signal` doing an exact key match** instead of a substring
  check, so `sentiment_score` or `confidence_threshold` slips through.
- **`build_escalation_criteria` paraphrasing the examples** instead of embedding
  them verbatim — the model needs the concrete shots, and the test checks for the
  literal strings.

## Checklist

- [ ] `decide` implements the seven checks in priority order.
- [ ] `decide` reads neither `sentiment` nor `self_reported_confidence`.
- [ ] Multiple matches → `ASK_CLARIFY`; policy gap/silent/ambiguous → `ESCALATE`.
- [ ] Explicit/reiterated human request → `ESCALATE` first, no investigation.
- [ ] `uses_unreliable_signal` recurses and does substring matching.
- [ ] `build_escalation_criteria` states explicit criteria and embeds every
      example verbatim; raises `ValueError` on empty input.
- [ ] `LAB_TARGET=solution uv run pytest lab-12-escalation` is green.
- [ ] Plain `uv run pytest lab-12-escalation` fails until `starter/` is done.
