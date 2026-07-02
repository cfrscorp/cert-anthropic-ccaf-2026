# Lab 01: Claude API Fundamentals

_Task statements: Claude API appendix (messages, system prompts, max_tokens, stop_reason values) · Difficulty 1/10 · Est 0:45 · Prerequisites: None_

## Objective

Learn the shape of the Claude Messages API by writing three small, testable
helpers:

- send a single request and read the assistant's text back,
- carry a multi-turn conversation by threading history, and
- branch on `stop_reason` the way real agent code must.

You will work only against a deterministic mock of the Anthropic SDK, so no API
key and no network are needed.

## Background

Every call to Claude goes through one endpoint: `client.messages.create(...)`.
The **request** carries:

- `model` — which Claude model to use (e.g. `claude-opus-4-8`).
- `max_tokens` — a hard cap on how many tokens the model may generate. **This is
  required.** If generation hits the cap, the response is truncated.
- `system` — an optional system prompt that sets role/behavior. It is a separate
  field, *not* a message with `role: "system"`. Omit it when you don't need one.
- `messages` — the conversation so far, a list of `{"role", "content"}` turns
  where `role` is `"user"` or `"assistant"`. The first turn must be `user`.

The **response** object carries:

- `content` — a **list of content blocks**, not a plain string. A text block has
  `type == "text"` and a `.text` attribute. (Other block types exist, e.g.
  `tool_use`.) To get the assistant's text you concatenate the text blocks.
- `stop_reason` — *why* generation stopped. The three you handle here:
  - `"end_turn"` — Claude finished naturally; the text is the final answer.
  - `"max_tokens"` — the `max_tokens` cap was hit; output is likely truncated.
  - `"tool_use"` — Claude wants to call a tool; you execute it and send the
    result back on the next turn. This branch is the heart of the agentic loop
    you will build in later labs.
- `usage` — input/output token counts.

The API is **stateless**: it does not remember prior turns. To keep a
conversation coherent you resend the entire `messages` history on every call,
appending the assistant's reply so the next turn has full context.

Two conventions this lab (and the whole program) follows:

- **Dependency injection.** Core logic takes an injected `client` parameter
  instead of constructing `anthropic.Anthropic()` internally. That is what lets
  the tests pass a mock. Build the real client once at the edge of your program.
- **Text blocks, not strings.** Always read text by filtering `resp.content` to
  text blocks — never assume `resp.content` is a string.

## Tasks

Implement the three functions in `starter/client_basics.py` so the tests pass.
Keep the same public signatures.

1. **`ask(client, prompt, *, system=None, max_tokens=1024) -> str`** — Send one
   user message. Forward `model`, `max_tokens`, and the `messages` list. Include
   `system` only when it is not `None`. Return the concatenated text of the
   response's text blocks.
2. **`continue_conversation(client, history, user_message) -> tuple[str, list]`**
   — Append the new user turn to a *copy* of `history`, send the full history,
   then append the assistant reply. Return `(assistant_text, new_history)`.
   Do not mutate the caller's `history` list.
3. **`describe_stop_reason(resp) -> str`** — Return a distinct, human-readable
   explanation for each of `"end_turn"`, `"max_tokens"`, and `"tool_use"`, plus
   a sensible fallback for anything else.

## Deliverables

- A completed `starter/client_basics.py` with all three functions implemented
  and no remaining `NotImplementedError`.
- All tests in `tests/test_lab01.py` passing against your starter code.

## How to verify

From the `labs/` directory:

```
uv run pytest lab-01-claude-api-fundamentals
```

To check your work against the reference solution instead of your own:

```
LAB_TARGET=solution uv run pytest lab-01-claude-api-fundamentals
```

## Stretch goals

- Add a `usage_summary(resp) -> str` helper that reports input/output tokens
  from `resp.usage`, and a test for it.
- Extend `ask` to accept a `model` keyword (defaulting to `DEFAULT_MODEL`) and
  assert it is forwarded.
- Handle the additional real-world `stop_reason` values `"stop_sequence"`,
  `"pause_turn"`, and `"refusal"` in `describe_stop_reason`, and add tests.
- Write a tiny runnable demo CLI (`demo.py`) that calls `ask` against a
  `MockAnthropic` and prints the result. Follow the runnable-script conventions:
  PEP 723 metadata, `argparse` with `-h/--help` and an Examples epilog, a
  module-level `__version__`, and a `--version` flag.
