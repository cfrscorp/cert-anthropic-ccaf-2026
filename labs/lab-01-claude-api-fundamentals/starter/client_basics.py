"""Starter: Claude Messages API fundamentals.

Implement the three functions below. Each takes an injected ``client`` (real or
mock) that exposes ``client.messages.create(**kwargs)`` and returns a response
object with ``.content`` (a list of content blocks), ``.stop_reason``, and
``.usage`` — the same shape as the real Anthropic SDK.

Rules:
- Never construct ``anthropic.Anthropic()`` inside these functions. Accept the
  injected ``client`` so the tests can pass a mock.
- A response's ``content`` is a *list of blocks*, not a string. Text blocks have
  ``type == "text"`` and a ``.text`` attribute.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-01-claude-api-fundamentals -q
"""

from __future__ import annotations

from typing import Any

# The default model. Grounded in the Claude API skill's current-models table.
DEFAULT_MODEL = "claude-opus-4-8"


def ask(
    client: Any,
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Send a single user message to Claude and return the assistant's text.

    TODO:
      1. Build the request kwargs: model=DEFAULT_MODEL, max_tokens, and a
         messages list containing one user turn: {"role": "user", "content": prompt}.
      2. Only include `system` in the kwargs when it is not None.
      3. Call client.messages.create(**kwargs).
      4. Return the concatenated text of every text block in resp.content
         (filter to blocks whose type == "text" and join their .text).
    """
    raise NotImplementedError("TODO: implement ask()")


def continue_conversation(
    client: Any,
    history: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Append a user turn, call Claude, and append the assistant turn back.

    The Messages API is stateless — you must resend the full history each call.

    TODO:
      1. Build the messages to send WITHOUT mutating the caller's list. Using
         `+` is the easy way: sent = history + [{"role": "user", "content": user_message}].
      2. Call client.messages.create(model=DEFAULT_MODEL, max_tokens=1024,
         messages=sent).
      3. Extract the assistant text (concatenate the text blocks).
      4. Build new_history = sent + [{"role": "assistant", "content": <assistant text>}].
         (Building fresh lists with `+` keeps the caller's history untouched and
         avoids mutating the list you just passed to create.)
      5. Return (assistant_text, new_history).
    """
    raise NotImplementedError("TODO: implement continue_conversation()")


def describe_stop_reason(resp: Any) -> str:
    """Map a response's ``stop_reason`` to a human-readable explanation.

    TODO: branch on resp.stop_reason and return a distinct explanation for each:
      - "end_turn"   -> Claude finished naturally; use the text.
      - "max_tokens" -> hit the cap, output likely truncated; raise max_tokens/stream.
      - "tool_use"   -> Claude wants a tool; execute it and return results next turn.
    Return a sensible fallback string for any other value.
    """
    raise NotImplementedError("TODO: implement describe_stop_reason()")
