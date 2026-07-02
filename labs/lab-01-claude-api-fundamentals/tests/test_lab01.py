"""Deterministic tests for Lab 01: Claude API Fundamentals.

These run offline against the MockAnthropic client. They import the module under
test from starter/ by default, or from solution/ when LAB_TARGET=solution.
"""

from __future__ import annotations

from labkit import lab_module
from mock_anthropic import MockAnthropic, text_response, tool_use_response

mod = lab_module(__file__, "client_basics")


# --------------------------------------------------------------------------- #
# ask()                                                                        #
# --------------------------------------------------------------------------- #
def test_ask_returns_assistant_text():
    client = MockAnthropic(responses=[text_response("Bonjour !")])
    assert mod.ask(client, "Say hello in French.") == "Bonjour !"


def test_ask_concatenates_multiple_text_blocks():
    from mock_anthropic import TextBlock, message

    client = MockAnthropic(
        responses=[message([TextBlock(text="Hello "), TextBlock(text="world")])]
    )
    assert mod.ask(client, "greet") == "Hello world"


def test_ask_forwards_max_tokens_and_model():
    client = MockAnthropic(responses=[text_response("ok")])
    mod.ask(client, "hi", max_tokens=256)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["max_tokens"] == 256
    assert call["model"]  # a model id is always forwarded
    assert call["messages"] == [{"role": "user", "content": "hi"}]


def test_ask_forwards_system_when_provided():
    client = MockAnthropic(responses=[text_response("ok")])
    mod.ask(client, "hi", system="You are terse.")

    assert client.calls[0]["system"] == "You are terse."


def test_ask_omits_system_when_none():
    client = MockAnthropic(responses=[text_response("ok")])
    mod.ask(client, "hi")

    # When no system prompt is given, it must not be forwarded at all.
    assert "system" not in client.calls[0]


def test_ask_default_max_tokens_is_1024():
    client = MockAnthropic(responses=[text_response("ok")])
    mod.ask(client, "hi")

    assert client.calls[0]["max_tokens"] == 1024


# --------------------------------------------------------------------------- #
# continue_conversation()                                                      #
# --------------------------------------------------------------------------- #
def test_continue_conversation_threads_history():
    client = MockAnthropic(
        responses=[
            text_response("Hi Alice!"),
            text_response("Your name is Alice."),
        ]
    )

    text1, history1 = mod.continue_conversation(client, [], "My name is Alice.")
    assert text1 == "Hi Alice!"
    assert history1 == [
        {"role": "user", "content": "My name is Alice."},
        {"role": "assistant", "content": "Hi Alice!"},
    ]

    text2, history2 = mod.continue_conversation(client, history1, "What's my name?")
    assert text2 == "Your name is Alice."
    # History grows by two turns (user + assistant) each round.
    assert len(history2) == 4
    assert history2[2] == {"role": "user", "content": "What's my name?"}
    assert history2[3] == {"role": "assistant", "content": "Your name is Alice."}


def test_continue_conversation_sends_full_history():
    client = MockAnthropic(
        responses=[text_response("A1"), text_response("A2")]
    )

    _, history1 = mod.continue_conversation(client, [], "U1")
    mod.continue_conversation(client, history1, "U2")

    # The second call must resend the whole conversation, ending with the new
    # user turn (the API is stateless).
    second_call_messages = client.calls[1]["messages"]
    assert second_call_messages == [
        {"role": "user", "content": "U1"},
        {"role": "assistant", "content": "A1"},
        {"role": "user", "content": "U2"},
    ]


def test_continue_conversation_does_not_mutate_input_history():
    client = MockAnthropic(responses=[text_response("reply")])
    original = [{"role": "user", "content": "prev"}, {"role": "assistant", "content": "old"}]
    snapshot = [dict(turn) for turn in original]

    mod.continue_conversation(client, original, "new question")

    assert original == snapshot  # caller's list untouched


# --------------------------------------------------------------------------- #
# describe_stop_reason()                                                       #
# --------------------------------------------------------------------------- #
def test_describe_stop_reason_end_turn():
    resp = text_response("done", stop_reason="end_turn")
    # A non-empty, human-readable explanation is returned.
    assert mod.describe_stop_reason(resp).strip()


def test_describe_stop_reason_distinguishes_all_three():
    end = mod.describe_stop_reason(text_response("x", stop_reason="end_turn"))
    maxt = mod.describe_stop_reason(text_response("x", stop_reason="max_tokens"))
    tool = mod.describe_stop_reason(tool_use_response("lookup", {"id": "1"}))

    # Each branch produces a different, non-empty explanation.
    explanations = {end, maxt, tool}
    assert len(explanations) == 3
    assert all(e.strip() for e in explanations)


def test_describe_stop_reason_max_tokens_mentions_truncation_or_limit():
    msg = mod.describe_stop_reason(text_response("x", stop_reason="max_tokens")).lower()
    assert "truncat" in msg or "limit" in msg or "max_tokens" in msg


def test_describe_stop_reason_tool_use_mentions_tool():
    msg = mod.describe_stop_reason(tool_use_response("lookup", {"id": "1"})).lower()
    assert "tool" in msg
