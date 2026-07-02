# Lab 01 Solution: Claude API Fundamentals

## Approach

Three thin wrappers over `client.messages.create`, each isolating one core idea
of the Messages API: single-shot requests (`ask`), stateless multi-turn
threading (`continue_conversation`), and control flow on `stop_reason`
(`describe_stop_reason`). A private `_text_of(resp)` helper concentrates the
"content is a list of blocks" detail in one place so the other functions read
cleanly.

## Key decisions & why

- **Injected `client`, never `anthropic.Anthropic()` inside the functions.**
  Dependency injection is what makes the code testable offline: the tests pass a
  `MockAnthropic`, production passes a real client. Constructing the client
  internally would force a network call and an API key into every unit test.
- **`system` is omitted when `None`.** The system prompt is an *optional* request
  field. Forwarding `system=None` is noise; building the kwargs dict
  conditionally keeps the request to exactly what was asked for and makes the
  "omit when absent" behavior directly assertable via `client.calls`.
- **Read text via text blocks, not `resp.content` directly.** `resp.content` is a
  `list` of blocks. `_text_of` filters to `type == "text"` and joins `.text`,
  which is correct even when a response mixes text with other block types and
  when the answer spans multiple text blocks.
- **`continue_conversation` copies the history.** The API is stateless, so the
  helper appends the user turn, resends everything, and appends the assistant
  reply — returning a ready-to-reuse history. It copies the input list first so
  a caller's history is never mutated as a side effect.
- **`describe_stop_reason` returns three distinct strings plus a fallback.** Real
  agent code branches on `stop_reason`; the explanations make the meaning of each
  value explicit (`end_turn` = done, `max_tokens` = truncated, `tool_use` =
  continue the loop).
- **`DEFAULT_MODEL = "claude-opus-4-8"`.** A current, valid model id. Because the
  tests use a mock, the exact string doesn't affect behavior — but using a real
  id keeps the example honest.

## Reference walkthrough

`ask`:
1. Build `kwargs` with `model`, `max_tokens`, and a one-element `messages` list.
2. Add `system` only if it is not `None`.
3. Call `client.messages.create(**kwargs)`.
4. Return `_text_of(resp)`.

`continue_conversation`:
1. `sent = history + [{"role": "user", "content": user_message}]` (new list — no
   in-place mutation of the caller's history).
2. Call `create(model=..., max_tokens=1024, messages=sent)`.
3. Extract assistant text with `_text_of`.
4. `new_history = sent + [{"role": "assistant", "content": assistant_text}]`.
5. Return `(assistant_text, new_history)`.

Building fresh lists with `+` (rather than `.append` on a shared list) matters:
the list handed to `create` must not be mutated afterward, or a client that
records requests by reference would show the later-appended assistant turn.

`describe_stop_reason`:
- Branch on `resp.stop_reason`; return one explanation each for `end_turn`,
  `max_tokens`, `tool_use`, and a fallback for anything else.

## Common mistakes

- **Treating `resp.content` as a string** (`return resp.content`). It is a list
  of blocks — this raises or returns the wrong type.
- **Forwarding `system=None`.** The `test_ask_omits_system_when_none` test asserts
  `"system" not in client.calls[0]`; unconditionally passing `system` fails it.
- **Mutating the input `history`.** Calling `history.append(...)` directly fails
  `test_continue_conversation_does_not_mutate_input_history` and causes subtle
  double-append bugs when a caller reuses the list.
- **Forgetting to append the assistant turn**, or appending it before the call so
  the model "sees" its own empty reply. Append *after* reading the response.
- **Not resending full history**, e.g. sending only the latest user message —
  breaks `test_continue_conversation_sends_full_history` and, in reality, loses
  all conversational context.
- **Returning the same string for every `stop_reason`** — fails the
  "distinguishes all three" test.

## Checklist

- [ ] `ask` forwards `model`, `max_tokens`, and `messages`; includes `system`
      only when provided; returns concatenated text.
- [ ] `continue_conversation` copies history, appends user + assistant turns,
      resends full history, returns `(text, new_history)`.
- [ ] `describe_stop_reason` handles `end_turn`, `max_tokens`, `tool_use`, and a
      fallback, each distinct.
- [ ] No `anthropic.Anthropic()` constructed inside the functions.
- [ ] `LAB_TARGET=solution uv run pytest lab-01-claude-api-fundamentals` is green.
- [ ] `uv run pytest lab-01-claude-api-fundamentals` is green against your code.
