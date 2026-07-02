# L19 — Solution Notes

## Approach

`orchestrator.py` provides the building blocks of a hub-and-spoke coordinator,
each a small pure function so it can be tested deterministically without a live
model:

- `AgentDefinition` — the SDK-style config (`name`, `description`,
  `system_prompt`, `allowed_tools`).
- `coordinator_can_spawn` — a one-line gate on the `Task` capability.
- `build_subagent_prompt` — assembles a **self-contained** prompt: goal +
  complete findings + quality criteria.
- `select_subagents` — maps a query to needed capabilities, classifies each
  registered agent, and returns the matching subset.
- `spawn_parallel` — turns a task list into `Task` tool_use blocks for one turn.
- `partition_scope` — curated/faceted decomposition that covers a topic's breadth.
- `run_coordination` — wires the above together over an injected `MockAnthropic`.

See `solution/orchestrator.py` for the full implementation.

## Key decisions & why

- **`allowedTools` must include `"Task"` (1.3).** Spawning is a capability, not a
  given. `coordinator_can_spawn` and `spawn_parallel` both enforce it; a
  coordinator without `Task` can only answer directly.

- **Embed the COMPLETE prior findings, not a reference (1.3).** Subagents have
  isolated context and inherit nothing. `build_subagent_prompt` renders every
  finding in full — dicts key-by-key so metadata (`source`, `date`, `page`) stays
  bound to content (`claim`, `excerpt`), strings verbatim. A prompt that said
  "use the findings from earlier" would hand the subagent an empty context. The
  prompt also states the isolation contract explicitly so the intent is legible.

- **Separate content from metadata.** Rendering findings key-by-key preserves
  attribution through the handoff, which downstream synthesis needs to cite
  sources and reconcile conflicts (Task Statements 1.3 and 5.6).

- **Selection is dynamic (1.2), tied to Sample Question 7.** `select_subagents`
  infers capabilities from the query and returns only the relevant subset. This
  is the *opposite* failure surface from Q7: Q7's coordinator decomposed too
  *narrowly* (missing subdomains); here the risk we guard against is the reverse
  reflex of always running the *full* pipeline. A simple query gets one gatherer;
  a complex query gets web + docs + synthesis + report but still omits the
  fact-checker nobody asked for.

- **Parallel spawn = multiple Task blocks in ONE response (1.3).**
  `spawn_parallel` returns a *list* of blocks meant to be a single assistant
  turn's `content`. Emitting one Task per turn would serialize the subagents;
  emitting them together runs them concurrently. `run_coordination`'s test
  confirms both Task calls arrive in the first (and only) coordinator turn.

- **`partition_scope` covers breadth — the Sample Question 7 guard (1.2).** The
  Q7 coordinator split "creative industries" into digital art, graphic design,
  and photography — three visual-arts slices — so music, writing, and film were
  never researched, yet every subagent "succeeded." We defend against this two
  ways: a curated decomposition for known broad topics that deliberately spans
  music/writing/film/visual-arts/games/performing-arts, and a generic-facet
  fallback (history, market, technology, ethics, future, policy…) for arbitrary
  topics. The test asserts the creative-industries split contains music, writing,
  and film and is *not* all visual-arts entries.

- **Scoped `verify_fact` for the common case (Sample Question 9).** The synthesis
  agent's `allowed_tools` includes a narrow `verify_fact` tool (see the registry
  fixture) so the 85% simple fact-checks stay local, while the 15% deep
  verifications route back through the coordinator to the web-search agent. This
  is least-privilege: give the agent exactly what its common case needs, not the
  full web-search toolset (which would violate separation of concerns). Building
  this end-to-end is the stretch goal.

- **`run_coordination` proves isolation.** Each subagent call uses a **fresh**
  `messages=[{...}]` list containing only its self-contained prompt — never the
  coordinator's history. The router-based test asserts `len(req["messages"]) == 1`
  on every subagent turn and that the injected context marker is present.

## Reference walkthrough

Complex query: *"Write a comprehensive, cited report comparing recent news and
academic papers on AI in medicine."*

| Step | What happens |
|------|--------------|
| Capability inference | `news/recent` → `web_search`; `papers/academic` → `doc_analysis`; `comprehensive/compare` → `synthesis`; `report/cited` → `report`. Two gatherers ⇒ synthesis is required. |
| `select_subagents` | `["web_search", "doc_analysis", "synthesis", "report_writer"]` — `fact_checker` omitted (no verification requested). |
| Coordinator turn 1 | Emits parallel `Task` calls (web_search + doc_analysis) in **one** response; each prompt embeds the complete shared context. |
| Subagent runs | Each runs with a fresh 1-message conversation (isolated); returns findings. |
| Aggregate | `run_coordination` returns `delegations`, per-subagent `results`, and the `selected` list for observability. |

Contrast the *simple* query *"What are the latest headlines about AI?"* →
`["web_search"]` only.

`partition_scope("creative industries", 4)` →
`["music and audio production", "writing and publishing", "film and video
production", "visual arts and design"]` — breadth, not four visual-arts corners.

## Common mistakes

- **Referencing findings instead of embedding them** ("use the results above").
  Subagents inherit nothing; the prompt is all they get.
- **Summarising/truncating prior findings** before passing them, dropping the
  numbers, dates, and source URLs downstream synthesis needs.
- **Always running the full pipeline** regardless of query — wastes tokens and
  latency and is the opposite reflex to `select_subagents`.
- **Emitting one `Task` per turn** and calling it "parallel." Parallelism
  requires multiple Task blocks in a *single* response.
- **Forgetting the `Task` gate** — building a coordinator whose `allowed_tools`
  omits `"Task"` and wondering why it can't delegate.
- **Narrow decomposition** — partitioning a broad topic into variations of one
  subdomain (the Sample Question 7 trap).
- **Over-provisioning the synthesis agent** with the full web-search toolset
  instead of a scoped `verify_fact` (Sample Question 9).
- **Constructing a real client inside `run_coordination`.** Accept the injected
  `client` so tests can pass `MockAnthropic`.

## Checklist

- [ ] `coordinator_can_spawn` returns `True` only when `"Task"` ∈ `allowed_tools`.
- [ ] `build_subagent_prompt` embeds the **complete** findings verbatim, keeps
      metadata attached to content, includes goal + criteria, and states the
      no-inheritance contract.
- [ ] `select_subagents` returns a small subset for a simple query and a larger
      (but not full) subset for a complex one.
- [ ] `spawn_parallel` returns >1 `Task` block for one turn and raises
      `ValueError` for a non-spawning coordinator or empty tasks.
- [ ] `partition_scope("creative industries", …)` covers music, writing, and film.
- [ ] `run_coordination` emits parallel Task calls in one turn and runs each
      subagent with an isolated 1-message conversation.
- [ ] `LAB_TARGET=solution uv run pytest lab-19-multi-agent-orchestration` is green.
