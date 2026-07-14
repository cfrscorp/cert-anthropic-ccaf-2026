# L03 — Agentic Loop Fundamentals

| | |
|---|---|
| **Task statement** | 1.1 — Design and implement agentic loops for autonomous task execution |
| **Domain** | 1 — Agentic Architecture & Orchestration |
| **Difficulty** | 3 / 10 |
| **Estimated effort** | 1:30 |
| **Prerequisites** | L01 — Claude API Fundamentals |

## Objective

Implement the core **agentic loop** that lets Claude use tools autonomously: send
a request, inspect `stop_reason`, run any requested tools, feed the results back
into the conversation, and repeat until the model signals it is done. You will
build a single function, `run_agent`, and prove — with deterministic tests — that
its termination is **model-driven** (`stop_reason == "end_turn"`) rather than
based on brittle heuristics.

## Background

When you give Claude tools, a single `messages.create(...)` call does **not**
finish the task. Instead the model responds with `stop_reason == "tool_use"` and
one or more `tool_use` blocks describing the tools it wants to run. *Your code*
is responsible for the loop around the model:

```
user message
   │
   ▼
messages.create(...) ──► stop_reason?
                           │
              "tool_use" ──┤──► run each requested tool
                           │        │
                           │        ▼
                           │   append {"type":"tool_result", "tool_use_id":…} to messages
                           │        │
                           │        └──► loop back to messages.create(...)
                           │
              "end_turn" ──┴──► return the final assistant text  ✅ done
```

Two ideas do the heavy lifting:

- **`stop_reason` is the control signal.** Continue while it is `"tool_use"`;
  stop when it is `"end_turn"`. Nothing else decides termination.
- **Tool results are appended to the conversation** (as a `user` turn containing
  `tool_result` blocks whose `tool_use_id` matches the model's `tool_use` id).
  This is how the model "sees" what happened and reasons about the next step.

This is **model-driven** control flow: Claude decides which tool to call next
based on the accumulating context — as opposed to a hard-coded decision tree or a
fixed tool sequence you wrote in advance.

### Anti-patterns to Avoid (These Are Tested)

- ❌ **Parsing natural language to decide when to stop** (e.g. stopping because
  the reply contains "done" or "final answer"). Use `stop_reason`.
- ❌ **Treating "the assistant produced text" as completion.** A `tool_use` turn
  can *also* contain a text block. If you stop as soon as you see text, you abort
  mid-task.
- ❌ **Using an iteration cap as the primary stop.** A `safety_cap` is fine as a
  *backstop* against a runaway loop, but the normal exit is `end_turn`.

## Tasks

Edit `starter/agent_loop.py` and implement `run_agent`:

```python
run_agent(client, user_message, tools, tool_executor, *,
          model="claude-mock", max_tokens=1024, safety_cap=25) -> dict
```

1. **Seed the conversation** with the user's message:
   `messages = [{"role": "user", "content": user_message}]`.
2. **Loop.** On each pass, call
   `client.messages.create(model=..., max_tokens=..., messages=messages, tools=tools)`
   and count the iteration.
3. **Append the assistant turn** every iteration:
   `{"role": "assistant", "content": resp.content}`.
4. **Branch on `resp.stop_reason`:**
   - If `"tool_use"`: for each block in `resp.tool_use_blocks()`, call
     `tool_executor(block.name, block.input)` and collect a
     `{"type": "tool_result", "tool_use_id": block.id, "content": <output>}`
     block. Append them as one `user` turn, then continue the loop.
   - Otherwise (`"end_turn"`): capture `resp.text` as the final text and stop.
5. **Backstop with `safety_cap`.** If the loop reaches `safety_cap` model calls
   without an `end_turn`, `raise RuntimeError`. This must *not* be how the loop
   normally ends.
6. **Return** a dict with at least `{"final_text", "iterations", "messages"}`.

The `client` is injected — do not construct `anthropic.Anthropic()` inside the
function. Tests pass a `MockAnthropic`.

## Deliverables

- `starter/agent_loop.py` with a working `run_agent` (matches the public API in
  `solution/agent_loop.py`).
- All tests in `tests/test_lab03.py` passing against your `starter/`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-03-agentic-loop            # your work (starter/) — should pass when done
LAB_TARGET=solution uv run pytest lab-03-agentic-loop   # the reference solution — always green
```

The tests assert that a `[tool_use, tool_use, end_turn]` script produces exactly
3 model calls and 2 tool executions; that `tool_result` blocks are appended with
matching `tool_use_id`s and fed back into the next request; that a turn combining
text **and** `tool_use` does not stop the loop early; and that `safety_cap` halts
a model that always asks for a tool.

## Stretch Goals

- **Multiple tools per turn.** Extend a test so one assistant turn contains two
  `tool_use` blocks (use `mock_anthropic.message(...)` to build a custom turn)
  and confirm your loop executes both and appends two `tool_result` blocks in a
  single `user` turn.
- **Usage accounting.** Sum `resp.usage.input_tokens` / `output_tokens` across
  iterations and add a `usage` key to the returned dict.
- **Tool errors.** Have `tool_executor` raise for an unknown tool; catch it and
  append a `tool_result` with `{"is_error": True, ...}` so the model can recover,
  instead of crashing the loop.
- **Router-driven demo.** Use `MockAnthropic(router=...)` to return an `end_turn`
  only after it "sees" a particular `tool_result` in the request, mimicking a
  model that reasons over tool output.
