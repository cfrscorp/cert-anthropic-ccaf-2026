# L08 — Solution Notes

## Approach

Three pure functions map a task/issue description (a plain dict) to the choice the
exam guide prescribes. Each is a short boolean expression over named features, so
the *reasoning* is visible and every canonical scenario in `scenarios.md` is
reproducible by the tests.

- `choose_mode(task)` → `"plan"` if **any** plan trigger fires (architectural,
  multiple valid approaches, multi-file, or unclear scope), else `"direct"`.
- `refinement_strategy(issues)` → `"single_message"` if **any** issue interacts
  with the others, else `"sequential"`.
- `should_use_explore(task)` → `True` only when discovery is **verbose** *and* it
  would burden the main session (multi-phase or context-exhaustion risk).

See `solution/decisions.py` for the full implementation.

## Key decisions & why

- **Plan mode when complexity is stated up front (Sample Question 5).** The
  monolith→microservices task is architectural, multi-file, and has multiple valid
  approaches — all plan triggers. You enter plan mode *immediately* to explore
  dependencies and design service boundaries before touching code.
  - **Why not "start direct, switch to plan later" (Q5 option D)?** The complexity
    is already in the requirements; it is not something that *might* emerge. Waiting
    to switch risks committing to changes you have to unwind — the exact rework plan
    mode exists to prevent.
  - **Why not "direct execution with comprehensive upfront instructions" (Q5
    option C)?** That assumes you already know the correct structure without
    exploring the code. You don't — discovering service boundaries and dependencies
    is the whole point of the plan phase.
  - **Why not incremental direct execution (Q5 option B)?** Letting implementation
    "reveal" boundaries discovers dependencies late, when they are expensive to fix.

- **Direct execution for simple, well-scoped changes.** A single-file bug fix with a
  clear stack trace, or adding one date-validation conditional, has *no* plan
  triggers: one file, clear scope, no design choice. Plan mode here is pure
  overhead. The rule returns `"direct"` precisely when none of the triggers fire.

- **Multi-file (`> 1`) is itself a plan trigger.** The guide lists "multi-file
  modifications" alongside architectural and large-scale changes. Touching several
  files means coordinating edits and understanding cross-file impact, which benefits
  from a plan even absent an explicit architectural flag (scenario #5 vs the
  boundary test `test_multi_file_alone_forces_plan`).

- **Explore is gated on BOTH verbose discovery AND burden.** Isolating discovery in
  a subagent only pays off when the discovery is noisy *and* would otherwise crowd
  the main context (multi-phase work, or a real exhaustion risk). Verbose discovery
  that is quick and self-contained (`test_verbose_discovery_without_burden_is_not_
  explore`) does not justify the subagent overhead; and if there is no verbose
  discovery to isolate, `multi_phase` alone changes nothing
  (`test_multi_phase_without_verbose_discovery_is_not_explore`). This is why plan
  scenario #5 (a design *decision*, no discovery) uses plan mode but **not** Explore.

- **Combine plan + direct.** Scenarios #4 (plan the 45-file migration) and #7
  (directly execute one already-planned step) are the same overall effort split into
  a plan-for-investigation phase and a direct-for-implementation phase — the
  guide's recommended combination.

- **Single message for interacting fixes, sequential for independent ones.** When
  one fix reshapes another (a lock-ordering change that alters the race-condition
  fix; a schema change the serializer depends on), sending them together lets the
  model reconcile the coupling in one pass — fixing them one at a time would make
  each fix invalidate the last. Independent fixes are cleaner sequentially, so each
  small change is easy to verify. An empty list has nothing to reconcile, so it
  degenerates to `"sequential"`.

## Reference walkthrough

`choose_mode` on the two headline cases:

| Task | architectural | approaches | multi_file (`>1`) | clear_scope | triggers? | → |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| monolith→microservices | yes | yes | yes (60) | no | yes | **plan** |
| single-file bug fix | no | no | no (1) | yes | none | **direct** |

`should_use_explore` = `verbose_discovery AND (multi_phase OR context_exhaustion_risk)`:

| Task | verbose | multi_phase | ctx_risk | → |
|------|:---:|:---:|:---:|:---:|
| monolith→microservices | yes | yes | yes | **True** |
| choose-integration-approach | no | no | no | **False** |
| verbose-but-cheap lookup | yes | no | no | **False** |

`refinement_strategy` = `single_message` iff any issue interacts:

| Issues (`interacts_with_others`) | → |
|------|:---:|
| `[true, true]` | **single_message** |
| `[true, false]` | **single_message** |
| `[false, false, false]` | **sequential** |
| `[]` | **sequential** |

## Common mistakes

- **Treating multi-file changes as direct** because "each edit is small." Multiple
  files is a plan trigger — coordinating them is the complexity.
- **Switching to plan mode "later."** If the requirements already state the
  complexity, plan *up front* (the Q5 trap).
- **Spawning Explore for every discovery.** Gate it on verbose *and* burdensome; a
  cheap lookup doesn't need a subagent, and a design decision has no discovery to
  isolate.
- **Requiring `verbose_discovery` OR `multi_phase`.** It must be AND-with-a-burden:
  `multi_phase` alone (no verbose output) does not warrant Explore.
- **Fixing interacting issues sequentially.** Each sequential fix can invalidate the
  previous one; coupled fixes belong in a single message.
- **Fixing independent issues in one giant message.** Wastes the reviewability that
  small sequential iterations give you (and can cause the model to conflate them).
- **Impure functions.** No I/O or globals — the tests parametrize over pure inputs.
- **Returning booleans/strings inconsistently.** `choose_mode` and
  `refinement_strategy` return strings; `should_use_explore` returns a real `bool`
  (`is True`/`is False` is asserted).

## Checklist

- [ ] `choose_mode` returns `"plan"` on any of: architectural, multiple approaches,
      `multi_file_count > 1`, `clear_scope` false; else `"direct"`.
- [ ] Monolith→microservices → `"plan"`; single-file bug fix → `"direct"`.
- [ ] `refinement_strategy` returns `"single_message"` iff any issue interacts;
      empty list → `"sequential"`.
- [ ] `should_use_explore` returns `True` iff `verbose_discovery and (multi_phase or
      context_exhaustion_risk)`, and a real `bool`.
- [ ] Functions are pure (no I/O, no globals); defaults match the docstrings.
- [ ] `uv run pytest lab-08-plan-mode-and-refinement` passes on your `starter/`.
- [ ] `LAB_TARGET=solution uv run pytest lab-08-plan-mode-and-refinement` is green.
