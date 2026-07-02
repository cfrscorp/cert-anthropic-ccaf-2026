# Canonical scenarios — L08

These are the reference cases for this lab. They are the single source of truth
for both the learner (read them to understand the decision boundaries) and the
tests (`tests/test_lab08.py` mirrors these exact rows and asserts the labels). If
you change a scenario here, update the matching entry in the test file too.

Each **mode scenario** is a `task` dict passed to both `choose_mode(task)` and
`should_use_explore(task)`. Each **refinement scenario** is an `issues` list
passed to `refinement_strategy(issues)`.

## Task features (recap)

`choose_mode` reads: `multi_file_count` (int), `architectural` (bool),
`multiple_valid_approaches` (bool), `clear_scope` (bool, default True).

`should_use_explore` reads: `verbose_discovery`, `multi_phase`,
`context_exhaustion_risk` (all bool, default False).

`refinement_strategy` reads, per issue: `interacts_with_others` (bool).

## Mode + Explore scenarios

| # | id | multi_file_count | architectural | multiple_valid_approaches | clear_scope | verbose_discovery | multi_phase | context_exhaustion_risk | → choose_mode | → should_use_explore |
|---|----|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `monolith-to-microservices` | 60 | true | true | false | true | true | true | **plan** | **True** |
| 2 | `single-file-bugfix-stack-trace` | 1 | false | false | true | false | false | false | **direct** | **False** |
| 3 | `add-date-validation-conditional` | 1 | false | false | true | false | false | false | **direct** | **False** |
| 4 | `library-migration-45-files` | 45 | false | true | false | true | true | true | **plan** | **True** |
| 5 | `choose-integration-approach` | 2 | true | true | false | false | false | false | **plan** | **False** |
| 6 | `add-null-guard-one-function` | 1 | false | false | true | false | false | false | **direct** | **False** |
| 7 | `execute-planned-migration-step` | 1 | false | false | true | false | false | false | **direct** | **False** |
| 8 | `map-unfamiliar-codebase` | 1 | false | false | false | true | true | true | **plan** | **True** |

Notes:

- **#1 monolith→microservices** is the Sample Question 5 case. Architectural +
  multi-file + multiple approaches — the complexity is *stated up front*, so you
  enter plan mode immediately (not "switch later", not "direct with upfront
  instructions"). Its discovery phase is verbose and multi-phase, so you delegate
  it to Explore during the plan/investigation stage.
- **#2 single-file bug fix with a clear stack trace** is the canonical direct
  case: one file, clear scope, no architectural or design choices.
- **#5 choose-integration-approach** shows plan mode driven by *design choice*
  (multiple valid approaches + architectural) even though few files change — and
  it needs no Explore because there is no verbose discovery, just a decision.
- **#7 execute-planned-migration-step** is the "combine" pattern: you *planned*
  the migration (#4), and now execute one already-designed step in one module —
  that implementation step is direct.
- **#8 map-unfamiliar-codebase** is plan-for-investigation: scope is open-ended
  (`clear_scope=false`), and the noisy exploration goes to Explore.

## Refinement scenarios

| # | id | issues (`interacts_with_others`) | → refinement_strategy |
|---|----|---|:---:|
| R1 | `coupled-lock-and-race` | `[true, true]` | **single_message** |
| R2 | `independent-typo-and-docstring` | `[false, false]` | **sequential** |
| R3 | `schema-and-serializer-coupled` | `[true, false]` | **single_message** |
| R4 | `three-independent-lint-fixes` | `[false, false, false]` | **sequential** |
| R5 | `no-issues` | `[]` | **sequential** |

Notes:

- **R1 / R3**: at least one fix changes another (e.g. a lock ordering fix that
  reshapes the race-condition fix; a schema change the serializer depends on).
  Send them together in one detailed message so the model reconciles the coupling.
- **R2 / R4**: unrelated fixes that cannot affect one another — iterate
  sequentially so each change stays small and reviewable.
- **R5**: nothing to reconcile → sequential (the degenerate case).
