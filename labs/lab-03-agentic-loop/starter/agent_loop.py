"""Starter scaffold: implement a minimal, model-driven agentic loop.

Fill in ``run_agent`` so it drives Claude through the agentic loop:

    1. Send the conversation to the model via ``client.messages.create(...)``.
    2. Inspect ``resp.stop_reason``.
    3. If it is ``"tool_use"``: run every requested tool with ``tool_executor``,
       append the results as ``tool_result`` blocks, and loop again.
    4. If it is ``"end_turn"``: stop and return the model's final text.

Termination MUST be driven by ``stop_reason``. Do NOT:
    - parse the assistant's natural-language text to decide when to stop,
    - treat "there is assistant text" as a completion signal (a tool_use turn
      can also contain text), or
    - use ``safety_cap`` as the normal way to stop (it is only a backstop).

The client is injected so tests can pass a deterministic mock. Do not construct
``anthropic.Anthropic()`` inside this function.

Run the tests from the ``labs/`` directory:  uv run pytest lab-03-agentic-loop
"""

from __future__ import annotations

from typing import Any, Callable

__all__ = ["run_agent"]


def run_agent(
    client: Any,
    user_message: str,
    tools: list[dict[str, Any]],
    tool_executor: Callable[[str, dict[str, Any]], Any],
    *,
    model: str = "claude-mock",
    max_tokens: int = 1024,
    safety_cap: int = 25,
) -> dict[str, Any]:
    """Run the agentic loop until ``stop_reason == "end_turn"``.

    Returns a dict with at least ``final_text`` (str), ``iterations`` (int), and
    ``messages`` (the full conversation list). Raise ``RuntimeError`` if
    ``safety_cap`` model calls happen without ever reaching ``end_turn``.

    See the module docstring and README.md for the required control flow.
    """
    # TODO: seed the conversation with the user's message.
    # TODO: loop:
    #   - as a backstop, raise RuntimeError if you have hit safety_cap calls;
    #   - call client.messages.create(model=..., max_tokens=..., messages=...,
    #     tools=...);
    #   - append the assistant turn ({"role": "assistant", "content": resp.content});
    #   - if resp.stop_reason == "tool_use": for each block in
    #     resp.tool_use_blocks(), call tool_executor(block.name, block.input) and
    #     append a user turn whose content is a list of
    #     {"type": "tool_result", "tool_use_id": block.id, "content": <output>};
    #   - otherwise capture resp.text as final_text and stop.
    # TODO: return {"final_text": ..., "iterations": ..., "messages": ...}.
    raise NotImplementedError("Implement run_agent (see README.md and the TODOs).")
