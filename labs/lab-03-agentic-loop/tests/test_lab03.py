"""Deterministic tests for L03 — Agentic Loop Fundamentals.

These exercise the model-driven loop contract from Task Statement 1.1:
termination is decided by ``stop_reason``, tool results are appended to history,
and a safety cap only serves as a backstop.

Run from labs/:  uv run pytest lab-03-agentic-loop
Validate ref:     LAB_TARGET=solution uv run pytest lab-03-agentic-loop
"""

from __future__ import annotations

import pytest
from labkit import lab_module
from mock_anthropic import MockAnthropic, text_response, tool_use_response

agent = lab_module(__file__, "agent_loop")

TOOLS = [
    {
        "name": "lookup_order",
        "description": "Look up an order by id.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    }
]


def make_executor(calls):
    """A tool executor that records (name, input) and returns a canned result."""

    def _executor(name, tool_input):
        calls.append((name, tool_input))
        return f"result for {name}({tool_input})"

    return _executor


def test_loop_runs_until_end_turn():
    """[tool_use, tool_use, end_turn] -> 3 model calls, 2 tool executions."""
    client = MockAnthropic(
        responses=[
            tool_use_response("lookup_order", {"order_id": "A1"}, tool_id="t1"),
            tool_use_response("lookup_order", {"order_id": "A2"}, tool_id="t2"),
            text_response("Both orders shipped Tuesday."),
        ]
    )
    tool_calls: list = []
    result = agent.run_agent(
        client,
        "Where are my orders A1 and A2?",
        TOOLS,
        make_executor(tool_calls),
    )

    # Exactly 3 model calls (one per scripted response).
    assert result["iterations"] == 3
    assert len(client.calls) == 3
    # Exactly 2 tool executions (one per tool_use turn).
    assert len(tool_calls) == 2
    assert tool_calls[0] == ("lookup_order", {"order_id": "A1"})
    # Final text comes from the end_turn turn.
    assert result["final_text"] == "Both orders shipped Tuesday."


def test_tool_results_appended_with_matching_ids():
    """Each tool_use is answered by a tool_result with the same tool_use_id."""
    client = MockAnthropic(
        responses=[
            tool_use_response("lookup_order", {"order_id": "A1"}, tool_id="toolu_abc"),
            text_response("Done."),
        ]
    )
    result = agent.run_agent(client, "Check A1", TOOLS, make_executor([]))

    # Collect every tool_result block that was appended to history.
    tool_results = [
        block
        for msg in result["messages"]
        if msg["role"] == "user" and isinstance(msg["content"], list)
        for block in msg["content"]
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]
    assert len(tool_results) == 1
    assert tool_results[0]["tool_use_id"] == "toolu_abc"
    assert tool_results[0]["content"] == "result for lookup_order({'order_id': 'A1'})"

    # The second model call must have seen the tool_result in its messages,
    # proving results are fed back into context between iterations.
    second_request_messages = client.calls[1]["messages"]
    assert any(
        isinstance(m["content"], list)
        and any(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in m["content"]
        )
        for m in second_request_messages
    )


def test_does_not_stop_on_assistant_text_alongside_tool_use():
    """A turn with BOTH text and a tool_use must NOT terminate the loop.

    Termination is driven by stop_reason, not by the presence of assistant text.
    """
    client = MockAnthropic(
        responses=[
            # stop_reason is still "tool_use" even though text is present.
            tool_use_response(
                "lookup_order",
                {"order_id": "A1"},
                tool_id="t1",
                text="Let me look that up for you.",
            ),
            text_response("Your order shipped Tuesday."),
        ]
    )
    tool_calls: list = []
    result = agent.run_agent(client, "Where is A1?", TOOLS, make_executor(tool_calls))

    # The loop continued past the text+tool_use turn and executed the tool.
    assert len(tool_calls) == 1
    assert result["iterations"] == 2
    assert result["final_text"] == "Your order shipped Tuesday."


def test_safety_cap_prevents_infinite_loop():
    """A model that always returns tool_use must be stopped by the backstop."""

    def always_tool_use(req, calls):
        return tool_use_response("lookup_order", {"order_id": "loop"}, tool_id="t")

    client = MockAnthropic(router=always_tool_use)

    with pytest.raises(RuntimeError) as excinfo:
        agent.run_agent(
            client,
            "spin forever",
            TOOLS,
            make_executor([]),
            safety_cap=5,
        )

    # The loop actually ran and was stopped by the backstop, not by some other
    # error path (NotImplementedError is a RuntimeError subclass, so exclude it).
    assert not isinstance(excinfo.value, NotImplementedError)
    # The cap is honored exactly: safety_cap model calls, then it stops.
    assert len(client.calls) == 5
