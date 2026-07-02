# L13 — Solution Notes

## Approach

Model named sessions as a `name -> list[message]` map, optionally mirrored to a
JSON file so state survives across process runs (the on-disk persistence is what
makes `--resume` possible in the real tool). Everything else is careful
copy-semantics plus two small pure functions that encode the decisions from Task
Statement 1.7.

The whole lab hinges on one discipline: **copy on the boundaries.** `save`,
`resume`, and `fork` all deep-copy so that stored history and each branch are
independent of the caller's working lists and of each other.

## Key decisions & why

### When to resume vs. restart with a summary

`should_resume(prior_results_stale)` is deliberately a one-liner, because the
*judgment* is the point, not the code:

- **Resume** when prior context is mostly valid. Resuming is cheap and keeps the
  agent's full, hard-won context (files it read, conclusions it drew). Throwing
  that away needlessly is wasteful.
- **Restart with a structured summary** when prior tool results are stale.
  Resuming replays old tool results *as if still true*. If the code changed, the
  agent reasons over a world that no longer exists — often worse than starting
  fresh. A new session seeded with a concise, current summary is **more
  reliable** because there is no misleading history to override.

The trap is treating resume as always-better because it is cheaper. Stale tool
results are actively harmful, not merely unhelpful.

### Why fork must be a deep copy

`fork_session` exists to explore **divergent approaches from a shared baseline**:
do the expensive analysis once, then branch it. That only works if the branches
are *independent* — the entire value proposition collapses if progress in
`approach_a` mutates `approach_b` or the baseline. A shallow copy shares the
nested message objects, so appending is fine but editing anything inside a
message silently corrupts siblings. `copy.deepcopy` is the correct, boring answer
and `test_fork_deep_copies_nested_structures` specifically catches a shallow-copy
implementation.

### Targeted re-analysis over full re-exploration

When resuming after edits, `inject_file_change_notice` names the exact files that
changed so the agent re-reads *only* those, rather than either trusting stale
readings or re-exploring the whole tree. It returns a new list and never mutates
the caller's — same copy-on-the-boundary discipline.

## Reference walkthrough

1. **`__init__`** keeps `self.path` (or `None`) and `self._sessions`. If the file
   exists, load it with `json.loads`.
2. **`_flush`** writes `self._sessions` back to disk when a path is set (creating
   parent dirs). Called after every mutation.
3. **`save`** stores `copy.deepcopy(messages)` then flushes.
4. **`resume`** raises `KeyError` for unknown names, else returns
   `copy.deepcopy(...)` so callers mutate their copy, not the store.
5. **`fork`** guards against unknown source and duplicate target names, then
   deep-copies the baseline into the new name and returns it.
6. **`list_sessions`** returns `sorted(self._sessions)`.
7. **`should_resume`** → `"restart_with_summary"` if stale else `"resume"`.
8. **`inject_file_change_notice`** deep-copies the input, returns it unchanged for
   an empty `changed_files`, else appends one `user` turn naming each file.

## Common mistakes

- **Shallow copy (or no copy) in `fork`/`save`/`resume`.** The branches or the
  store end up aliasing the caller's lists; a mutation in one place shows up in
  another. Use `copy.deepcopy`.
- **Mutating the input in `inject_file_change_notice`.** `messages.append(...)`
  edits the caller's list. Build and return a new list.
- **Getting the `should_resume` polarity backwards.** Stale →
  `restart_with_summary`; fresh → `resume`.
- **Not persisting / not reloading.** If `save` doesn't flush or `__init__`
  doesn't load, a reopened store won't see prior sessions and the
  cross-instance test fails.
- **Silent overwrite on `fork`.** Forking onto an existing name should error, not
  clobber a branch you were exploring.

## Checklist

- [ ] `save` + `resume` round-trips history exactly.
- [ ] A JSON-backed session is visible from a freshly constructed store.
- [ ] `fork` produces an independent branch; appending/editing it leaves the
      baseline unchanged (including nested content).
- [ ] `list_sessions` is sorted and includes forks.
- [ ] `should_resume(True) == "restart_with_summary"`, `should_resume(False) ==
      "resume"`.
- [ ] `inject_file_change_notice` references every changed file, is a no-op for
      `[]`, and never mutates the input.
- [ ] `LAB_TARGET=solution uv run pytest lab-13-session-state` is green;
      `uv run pytest lab-13-session-state` fails against the starter.
