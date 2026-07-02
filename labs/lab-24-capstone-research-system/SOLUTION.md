# L24 — Solution Notes

## Approach

The system is four small modules that compose into one `run_research` pipeline:

- **`agents.py`** — the hub-and-spoke `AgentDefinition` registry plus tool
  schemas. The coordinator holds `Task`; each subagent holds only its role's
  tools; synthesis holds the single scoped `verify_fact`.
- **`coordinator.py`** — `partition_scope` (broad, covering decomposition),
  `select_subagents` (dynamic), `build_subagent_prompt` (embeds full prior
  findings), `spawn_parallel` (one turn, many `Task` calls), `run_subagent`
  (findings or structured error), and `run_research` (the integration).
- **`errors.py`** — `build_error_context` / `handle_timeout` (structured
  propagation) and `classify_result` (access failure vs. empty success).
- **`synthesis.py`** — `merge_claims` (provenance), `annotate_conflict` (keep
  both), `coverage_annotations`, `render_by_type`, and `verify` (scoped tool vs.
  coordinator routing).

`run_research` flow: `partition_scope(topic)` → `select_subagents` →
`spawn_parallel` (coordinator emits parallel `Task` calls in one turn) → run each
subagent, collecting findings or structured errors → `synthesize` (merge, detect
conflicts, annotate coverage, render). A timeout in one subagent becomes a
coverage gap; the rest of the report is produced normally.

## Key decisions & why (mapped to the Sample Questions)

### Sample Q7 — broad decomposition (correct answer: **B**)
The reported bug was the coordinator decomposing "creative industries" into only
*digital art / graphic design / photography* — all visual arts — silently
dropping music, writing, and film. The root cause is **too-narrow task
decomposition by the coordinator** (B), not a downstream agent (A/C/D all blame
agents that were working correctly within their assigned scope).

- `expected_facets` anchors decomposition to the topic's real breadth, so
  `partition_scope` covers all four facets by construction.
- `repair_coverage` demonstrates the iterative-refinement rescue: given a narrow
  proposal, it appends partitions for every missing facet.
- **Distractor trap:** "add coverage-gap detection to synthesis" (A) treats the
  symptom downstream. Synthesis coverage annotations are valuable (we implement
  them!) but they cannot invent findings for a domain that was never assigned.

### Sample Q8 — error propagation (correct answer: **A**)
On a `web_search` timeout, `run_subagent` catches `TimeoutError`/`ConnectionError`
and returns `handle_timeout(...)` → **structured error context**: `failure_type`,
`attempted_query`, `partial_results`, `alternatives` (A). `run_research` then
proceeds with partial results, and the failed facet shows up as a coverage gap.

- **Distractor B** (generic "search unavailable" after silent retries) hides the
  context the coordinator needs — our error object carries the specifics.
- **Distractor C** (empty result marked successful) is exactly what
  `classify_result` exists to prevent: it separates `access_failure` from
  `empty_success` so a timeout is never mistaken for "no matches."
- **Distractor D** (propagate exception, kill the workflow) throws away
  recoverable progress — `run_research` keeps going with what succeeded.

### Sample Q9 — scoped verification (correct answer: **A**)
`verify` applies least privilege: a **simple** claim (date, name, statistic) is
checked with the synthesis agent's own scoped `verify_fact` tool in one forced
tool call — no coordinator round-trip. A **complex** claim (interpretive, causal,
multi-source) routes back through the coordinator **without** calling
`verify_fact` (A).

- **Distractor B** (batch all verifications to the end) creates blocking
  dependencies when later synthesis steps need earlier verified facts.
- **Distractor C** (give synthesis the full search toolset) over-provisions and
  breaks separation of concerns — that's why `synthesis.allowed_tools ==
  ("verify_fact",)` and the test asserts `web_search` is absent.
- **Distractor D** (speculative caching) can't reliably predict what synthesis
  will need.

### Task 5.6 — provenance & conflicts
`merge_claims` copies claims through without ever dropping `source` (and rejects
an unsourced claim so the bug surfaces). `annotate_conflict` groups by `metric`;
when values differ it keeps **every** observation with source name, url, and date,
and notes the date span so a temporal change (45% in 2023 → 62% in 2024) isn't
read as a contradiction. `render_by_type` renders statistics as a table, news as
prose, technical findings as a list — rather than flattening everything.

### Task 1.3 — context passing & parallelism
`build_subagent_prompt` serializes prior findings **in full** (`json.dumps(...,
indent=2, sort_keys=True)`) between explicit delimiters — never a summary —
because subagents have isolated context. `spawn_parallel` makes exactly **one**
`client.messages.create` call and returns the multiple `Task` blocks from that
single turn; parallelism is "many Task calls in one response," not many turns.

## Reference walkthrough

`run_research(client, "impact of AI on creative industries")` with a router where
the `film` subagent times out:

| Step | What happens |
|---|---|
| `partition_scope` | 4 partitions: visual arts, music, writing, film |
| `select_subagents` | `["web_search", "synthesis", "report"]` (no documents) |
| `spawn_parallel` | 1 coordinator call → 4 `Task` blocks (`spawned_tasks == 4`) |
| run web_search × visual arts/music/writing | `record_findings` → claims (incl. 45% and 62% conflict) |
| run web_search × film | `TimeoutError` → `handle_timeout` → structured error |
| `synthesize` | merge (provenance kept) → conflict on the AI-adoption metric (both 45%/62% retained) → coverage: film = **gap**, others supported |
| report | Markdown with well-established, contested (both values + dates), and a `GAP` line for film |

## Common mistakes

- **Narrow decomposition.** Partitioning into one sub-domain's facets. Cover the
  whole topic (Q7).
- **Summarizing prior findings** in the subagent prompt. Pass them **verbatim** —
  summarization is where provenance and detail get lost.
- **Spawning across turns.** Emitting one `Task` per turn is sequential, not
  parallel. Emit multiple in one response.
- **Giving synthesis the search toolset.** It gets `verify_fact` only; complex
  cases route through the coordinator (Q9).
- **Calling `verify_fact` for complex claims.** Classify first; don't call the
  tool for interpretive/multi-source questions.
- **Timeout = empty success.** Never mark a failed access as an empty result
  (Q8-C). Keep `access_failure` and `empty_success` distinct.
- **Killing the workflow on one failure.** Proceed with partial results and
  annotate the gap (Q8-D).
- **Picking one conflicting value.** Keep both with attribution + dates (Task 5.6).
- **Dropping `source` in merge.** Every merged claim must retain its provenance.
- **Constructing a real client.** Accept the injected `client`.

## Checklist

- [ ] Coordinator `allowed_tools` includes `"Task"`; synthesis is `("verify_fact",)` only.
- [ ] `partition_scope` covers music/writing/film for the creative-industries topic.
- [ ] `repair_coverage` fills missing facets from a narrow proposal.
- [ ] `select_subagents` includes `doc_analysis` only with documents; always synthesis + report.
- [ ] `build_subagent_prompt` embeds the FULL prior findings verbatim.
- [ ] `spawn_parallel` makes one `create` call and returns >1 `Task` block.
- [ ] `handle_timeout` returns failure type, attempted query, partial results, alternatives.
- [ ] `classify_result` separates `access_failure` / `empty_success` / `results`.
- [ ] `merge_claims` preserves each claim's source; rejects unsourced claims.
- [ ] `annotate_conflict` keeps both values with attribution + dates.
- [ ] `render_by_type` differs by content type (table / prose / list).
- [ ] `verify` uses forced `verify_fact` for simple, routes complex to coordinator.
- [ ] `run_research` proceeds with partial results + a coverage gap on timeout.
- [ ] `LAB_TARGET=solution uv run pytest lab-24-capstone-research-system` is green.
