"""Reference solution: Claude Messages API fundamentals.

These helpers wrap the core shape of the Claude Messages API: a single request
carries a ``model``, a ``max_tokens`` cap, an optional ``system`` prompt, and a
``messages`` list of ``{"role", "content"}`` turns. The response object exposes
``content`` (a list of content blocks), ``stop_reason``, and ``usage``.

Every function takes an injected ``client`` (dependency injection) rather than
constructing ``anthropic.Anthropic()`` internally, so tests can pass a mock and
production code can pass a real client. The real client is created *once* at the
edge of the program and threaded through.

    import anthropic
    client = anthropic.Anthropic()          # real client, made at the edge
    answer = ask(client, "Say hello in French.")
"""

from __future__ import annotations

from typing import Any

# The default model. Grounded in the Claude API skill's current-models table.
DEFAULT_MODEL = "claude-opus-4-8"


def _text_of(resp: Any) -> str:
    """Concatenate the text of every ``text`` content block in a response.

    A response's ``content`` is a *list of blocks*, not a string. Text blocks
    have ``type == "text"`` and a ``.text`` attribute; other block types (e.g.
    ``tool_use``) do not, so we filter to text blocks and join them. This mirrors
    the real SDK, where ``response.content`` is ``list[TextBlock | ToolUseBlock]``.
    """
    return "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )


def ask(
    client: Any,
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Send a single user message to Claude and return the assistant's text.

    Args:
        client: An Anthropic-like client (real or mock) exposing
            ``client.messages.create(**kwargs)``.
        prompt: The user's message text.
        system: Optional system prompt. When ``None`` it is omitted from the
            request entirely (the API treats the system prompt as optional; do
            not send ``system=None``).
        max_tokens: The hard cap on tokens the model may generate. Forwarded to
            the API. If the model hits this cap, ``stop_reason`` will be
            ``"max_tokens"`` (see ``describe_stop_reason``).

    Returns:
        The concatenated text of all text blocks in the response.
    """
    kwargs: dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    # Only include `system` when the caller supplied one — the system prompt is
    # optional, and forwarding an explicit None muddies the request.
    if system is not None:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    return _text_of(resp)


def continue_conversation(
    client: Any,
    history: list[dict[str, Any]],
    user_message: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Append a user turn, call Claude, and append the assistant turn back.

    The Messages API is stateless: to keep a conversation coherent you must
    resend the full history on every call. This helper does the bookkeeping —
    it appends the new user turn, sends the whole conversation, then appends the
    assistant's reply so the returned history is ready to pass straight back in.

    Args:
        client: An Anthropic-like client exposing ``client.messages.create``.
        history: Prior conversation turns as ``{"role", "content"}`` dicts. Not
            mutated — a new list is returned.
        user_message: The new user message to add.

    Returns:
        A ``(assistant_text, new_history)`` tuple. ``new_history`` is the input
        history plus the new user turn and the assistant's reply.
    """
    # Use `+` to build fresh lists rather than mutating in place. This keeps the
    # caller's `history` untouched, and — importantly — means the list handed to
    # `create` is never appended to afterward.
    sent_messages = history + [{"role": "user", "content": user_message}]

    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        messages=sent_messages,
    )
    assistant_text = _text_of(resp)

    new_history = sent_messages + [{"role": "assistant", "content": assistant_text}]
    return assistant_text, new_history


def describe_stop_reason(resp: Any) -> str:
    """Map a response's ``stop_reason`` to a human-readable explanation.

    ``stop_reason`` tells you *why* the model stopped generating, and correct
    code branches on it:

    - ``"end_turn"``   — Claude finished its response naturally. Use the text.
    - ``"max_tokens"`` — The ``max_tokens`` cap was hit and the output is likely
      truncated. Raise the cap (or stream) and retry.
    - ``"tool_use"``   — Claude wants to call a tool. Execute the requested
      tool(s) and send the results back for the next turn (the agentic loop).

    Args:
        resp: A response object exposing ``.stop_reason``.

    Returns:
        A human-readable explanation string.
    """
    reason = resp.stop_reason
    if reason == "end_turn":
        return "Claude finished its response naturally; use the text as the final answer."
    if reason == "max_tokens":
        return (
            "Claude hit the max_tokens limit and the response is likely truncated; "
            "raise max_tokens or stream, then retry."
        )
    if reason == "tool_use":
        return (
            "Claude wants to call a tool; execute the requested tool(s) and return "
            "the results in the next request to continue the agentic loop."
        )
    return f"Unrecognized stop_reason: {reason!r}."
