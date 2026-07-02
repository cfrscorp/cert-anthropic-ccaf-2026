# L03 — Solution Notes

## Approach

`run_agent` is a single `while True:` loop around `client.messages.create(...)`.
Each pass:

1. Checks the `safety_cap` backstop *before* calling the model.
2. Calls the model with the full running `messages` list plus `tools`.
3. Appends the assistant turn (`resp.content`) to history.
4. Branches on `resp.stop_reason`:
   - `"tool_use"` → execute every `resp.tool_use_blocks()` entry via
     `tool_executor`, append one `user` turn of `tool_result` blocks, and loop.
   - anything else (`"end_turn"`) → capture `resp.text` and break.
5. Returns `{"final_text", "iterations", "messages"}`.

See `solution/agent_loop.py` for the full implementation.

## Key decisions & why

- **`stop_reason` is the only termination signal.** The exam's Task Statement 1.1
  is explicit: continue when `stop_reason == "tool_use"`, terminate when it is
  `"end_turn"`. This makes the loop *model-driven* — Claude, not our code, decides
  when the task is complete.

- **Why NOT parse natural language to stop.** Wording like "I'm done" or "final
  answer" is unreliable: the model may say it mid-task, phrase it a thousand ways,
  or not say it at all. Parsing text couples your control flow to prose and breaks
  silently. `stop_reason` is a structured, contractual field — use it.

- **Why NOT treat "assistant produced text" as completion.** A single turn can
  contain a text block *and* a `tool_use` block (Claude "thinking out loud"
  before calling a tool). If you stop the moment you see text, you abort the task
  before the tool ever runs. Our loop checks `stop_reason`, so text alongside a
  `tool_use` is irrelevant — the loop continues. (`test_does_not_stop_on_
  assistant_text_alongside_tool_use` locks this in.)

- **Why NOT use an iteration cap as the primary stop.** An arbitrary "stop after N
  turns" cap will either cut off legitimate long tasks or, if set high, do nothing
  useful. It is not a correctness mechanism. We keep `safety_cap` strictly as a
  *backstop* against a genuinely stuck model (one that never emits `end_turn`), and
  we raise `RuntimeError` when it trips so the failure is loud, not silent.

- **Append the assistant turn every iteration, before tool results.** The
  `tool_result` blocks reference the assistant's `tool_use` ids, so the assistant
  turn must be in history first. Appending it also preserves the model's own prior
  reasoning across iterations.

- **Feed tool results back as a `user` turn.** Per the API contract, tool outputs
  are delivered as `tool_result` content blocks in a `user` message, each carrying
  the matching `tool_use_id`. This is *how the model incorporates new information* —
  without it, the next call would have no idea what the tools returned.

## Reference walkthrough

Script: `[tool_use(A1), tool_use(A2), end_turn("…Tuesday.")]`

| Iter | `create` call sees | `stop_reason` | Action |
|:----:|--------------------|:-------------:|--------|
| 1 | user msg | `tool_use` | run `lookup_order(A1)`; append assistant turn + tool_result(t1) |
| 2 | user, asst, tool_result(t1) | `tool_use` | run `lookup_order(A2)`; append assistant turn + tool_result(t2) |
| 3 | …+ tool_result(t2) | `end_turn` | capture text, break |

Result: `iterations == 3`, 2 tool executions, `final_text == "Both orders shipped Tuesday."`
The safety cap (default 25) is never approached — `end_turn` ends the loop.

For the runaway case, a router that always returns `tool_use` never yields
`end_turn`; the `iterations >= safety_cap` guard raises `RuntimeError` after
exactly `safety_cap` calls.

## Common mistakes

- **Checking `resp.text` (or scanning for keywords) to decide when to stop.**
  Breaks the moment the model narrates before a tool call. Use `stop_reason`.
- **Breaking the loop as soon as any text block appears.** Same bug — a
  `tool_use` turn can include text.
- **Making `safety_cap` the normal exit** (e.g. `for _ in range(safety_cap)`
  with no `end_turn` check). This is the anti-pattern the task calls out.
- **Forgetting to append the assistant turn**, or appending tool results under
  `role: "assistant"`. Tool results go in a **`user`** turn.
- **Mismatched `tool_use_id`.** Copy `block.id` from each `tool_use` block into
  its corresponding `tool_result`; do not invent ids.
- **Not appending tool results at all**, so each iteration re-sends the same
  context and the model loops or gives up.
- **Constructing a real client inside the function.** Accept the injected
  `client` so tests can pass `MockAnthropic`.

## Checklist

- [ ] Conversation seeded with the user message.
- [ ] Loop calls `client.messages.create` with `messages` and `tools` each pass.
- [ ] Assistant turn appended every iteration.
- [ ] `stop_reason == "tool_use"` → tools run, `tool_result` blocks appended as a
      `user` turn with matching `tool_use_id`s.
- [ ] `stop_reason == "end_turn"` → `final_text` captured, loop stops.
- [ ] No natural-language / text-presence checks used for termination.
- [ ] `safety_cap` is a backstop only and raises `RuntimeError` when tripped.
- [ ] Returns `{"final_text", "iterations", "messages"}`.
- [ ] `LAB_TARGET=solution uv run pytest lab-03-agentic-loop` is green.
