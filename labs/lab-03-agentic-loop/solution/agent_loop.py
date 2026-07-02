"""Reference implementation of a minimal, model-driven agentic loop.

The agentic loop is the control flow that lets Claude use tools autonomously:

    1. Send the conversation to the model.
    2. Inspect ``resp.stop_reason``.
    3. If ``stop_reason == "tool_use"``: run every requested tool, append the
       results to the conversation as a ``tool_result`` block, and iterate.
    4. If ``stop_reason == "end_turn"``: the model is done — return its text.

Termination is *model-driven*: it is decided entirely by ``stop_reason``, never
by parsing the assistant's natural-language text and never by an iteration count.
The ``safety_cap`` here is only a backstop against a runaway loop; it is not the
primary stopping mechanism.

The client is dependency-injected so tests can pass a deterministic mock. Any
object exposing ``client.messages.create(...)`` (the real Anthropic SDK or the
lab's ``MockAnthropic``) works.
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
    """Run the agentic loop until the model returns ``stop_reason == "end_turn"``.

    Args:
        client: An Anthropic-style client (real SDK or ``MockAnthropic``) whose
            ``client.messages.create(...)`` returns a message with
            ``.stop_reason``, ``.content``, ``.text`` and ``.tool_use_blocks()``.
        user_message: The learner/end-user's opening request.
        tools: Tool schemas passed through to the model on every call.
        tool_executor: Callable invoked as ``tool_executor(name, input)`` for each
            requested tool; its return value becomes the ``tool_result`` content.
        model: Model id to send on each request.
        max_tokens: Token budget per model call.
        safety_cap: Backstop only. If the loop makes this many model calls without
            ever seeing ``stop_reason == "end_turn"``, raise ``RuntimeError`` so a
            misbehaving model or tool cannot spin forever. This is NOT the normal
            way the loop ends.

    Returns:
        A dict with at least:
            - ``final_text``: text of the terminating ``end_turn`` message.
            - ``iterations``: number of model calls made.
            - ``messages``: the full conversation (user, assistant, tool_result
              turns) as it was sent to / grown by the loop.

    Raises:
        RuntimeError: if ``safety_cap`` model calls happen without an ``end_turn``.
    """
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_message}
    ]
    iterations = 0
    final_text = ""

    while True:
        # Backstop BEFORE calling the model, so we never exceed the cap.
        if iterations >= safety_cap:
            raise RuntimeError(
                f"safety_cap of {safety_cap} model calls exceeded without "
                "stop_reason == 'end_turn'; the loop is not making progress."
            )

        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            tools=tools,
        )
        iterations += 1

        # Always append the assistant turn so tool_result blocks can reference
        # the tool_use ids, and so the model sees its own prior reasoning.
        messages.append({"role": "assistant", "content": resp.content})

        # The ONLY termination signal is stop_reason. We do not read resp.text
        # to decide whether to stop; a tool_use turn may also contain text.
        if resp.stop_reason == "tool_use":
            tool_results: list[dict[str, Any]] = []
            for block in resp.tool_use_blocks():
                output = tool_executor(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
            # Feed results back as a user turn so the model reasons about the
            # next step with the new information in context.
            messages.append({"role": "user", "content": tool_results})
            continue

        # Any non-tool_use stop_reason means the model is finished asking for
        # tools; end_turn is the expected case. Capture the final text and stop.
        final_text = resp.text
        break

    return {
        "final_text": final_text,
        "iterations": iterations,
        "messages": messages,
    }
