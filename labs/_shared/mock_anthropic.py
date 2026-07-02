"""Deterministic mock of the Anthropic Python SDK for offline, free lab tests.

This module lets labs exercise agentic loops, tool use, structured output, and
batch processing WITHOUT calling the real Claude API. Responses are scripted, so
tests are fully deterministic.

It intentionally mimics only the *shape* of the real SDK that the labs rely on:

    client = MockAnthropic(responses=[...])          # or router=callable
    resp = client.messages.create(model=..., messages=..., tools=...)
    resp.stop_reason        # "tool_use" | "end_turn" | "max_tokens"
    resp.content            # list of TextBlock / ToolUseBlock
    resp.usage.input_tokens # ints

Build responses with the helpers:

    text_response("hi")                                  # stop_reason="end_turn"
    tool_use_response("get_customer", {"id": "C1"})      # stop_reason="tool_use"
    message(blocks=[...], stop_reason="tool_use")         # full control

For multi-turn agentic loops, pass a list of responses (consumed in order) or a
`router(request, history)` callable that returns the next response based on the
incoming request (e.g. inspect the last tool_result to decide what to say next).

Batch API (Message Batches) is mocked via `client.messages.batches`.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

__all__ = [
    "MockAnthropic",
    "TextBlock",
    "ToolUseBlock",
    "Usage",
    "Message",
    "text_response",
    "tool_use_response",
    "message",
]


# --------------------------------------------------------------------------- #
# Content blocks and message objects (attribute access like the real SDK)      #
# --------------------------------------------------------------------------- #
@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    name: str
    input: dict[str, Any]
    id: str = "toolu_mock"
    type: str = "tool_use"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Message:
    content: list[Any]
    stop_reason: str = "end_turn"
    id: str = "msg_mock"
    model: str = "claude-mock"
    role: str = "assistant"
    type: str = "message"
    usage: Usage = field(default_factory=Usage)

    def tool_use_blocks(self) -> list[ToolUseBlock]:
        """Convenience: all tool_use blocks in this message."""
        return [b for b in self.content if isinstance(b, ToolUseBlock)]

    @property
    def text(self) -> str:
        """Concatenated text of all text blocks."""
        return "".join(b.text for b in self.content if isinstance(b, TextBlock))


# --------------------------------------------------------------------------- #
# Response builders                                                            #
# --------------------------------------------------------------------------- #
_ids = itertools.count(1)


def text_response(text: str, stop_reason: str = "end_turn", **usage: int) -> Message:
    """A plain text answer (default stop_reason='end_turn')."""
    return Message(
        content=[TextBlock(text=text)],
        stop_reason=stop_reason,
        usage=Usage(**usage),
    )


def tool_use_response(
    name: str,
    tool_input: dict[str, Any],
    *,
    tool_id: str | None = None,
    text: str | None = None,
    stop_reason: str = "tool_use",
    **usage: int,
) -> Message:
    """A tool-call turn. Optionally prefix with an assistant text block."""
    blocks: list[Any] = []
    if text is not None:
        blocks.append(TextBlock(text=text))
    blocks.append(
        ToolUseBlock(name=name, input=tool_input, id=tool_id or f"toolu_{next(_ids)}")
    )
    return Message(content=blocks, stop_reason=stop_reason, usage=Usage(**usage))


def message(blocks: Iterable[Any], stop_reason: str = "end_turn", **kw: Any) -> Message:
    """Full control: supply your own list of blocks."""
    return Message(content=list(blocks), stop_reason=stop_reason, **kw)


# --------------------------------------------------------------------------- #
# The mock client                                                             #
# --------------------------------------------------------------------------- #
Router = Callable[[dict[str, Any], list[dict[str, Any]]], Message]


class _Messages:
    def __init__(self, responses: list[Message] | None, router: Router | None):
        self._responses = list(responses or [])
        self._router = router
        self.calls: list[dict[str, Any]] = []  # every request kwargs, in order

    def create(self, **kwargs: Any) -> Message:
        self.calls.append(kwargs)
        if self._router is not None:
            return self._router(kwargs, self.calls)
        if self._responses:
            return self._responses.pop(0)
        # Safe default so an under-scripted test fails loudly rather than hanging.
        return text_response(
            "[mock] no scripted response remaining", stop_reason="end_turn"
        )

    # Alias used by some labs.
    stream = create


@dataclass
class _BatchRequest:
    custom_id: str
    params: dict[str, Any]


@dataclass
class _BatchResult:
    custom_id: str
    result: dict[str, Any]  # {"type": "succeeded"|"errored", "message"|"error": ...}


class _Batch:
    def __init__(self, id: str, requests: list[_BatchRequest]):
        self.id = id
        self.processing_status = "in_progress"
        self.request_counts = {
            "processing": len(requests),
            "succeeded": 0,
            "errored": 0,
            "canceled": 0,
            "expired": 0,
        }
        self._requests = requests
        self._results: list[_BatchResult] = []


class _Batches:
    """Minimal Message Batches API mock.

    Provide a `handler(custom_id, params) -> ("succeeded"|"errored", payload)`
    to decide each request's outcome. Batches complete synchronously on create()
    for test determinism; SLA/timing is modeled in the lab code, not here.
    """

    def __init__(self, handler: Callable[[str, dict], tuple[str, Any]] | None = None):
        self._handler = handler or (lambda cid, params: ("succeeded", text_response("ok")))
        self._batches: dict[str, _Batch] = {}
        self._counter = itertools.count(1)

    def create(self, *, requests: list[dict[str, Any]]) -> _Batch:
        reqs = [_BatchRequest(r["custom_id"], r["params"]) for r in requests]
        batch = _Batch(f"msgbatch_{next(self._counter)}", reqs)
        for r in reqs:
            status, payload = self._handler(r.custom_id, r.params)
            key = "message" if status == "succeeded" else "error"
            batch._results.append(_BatchResult(r.custom_id, {"type": status, key: payload}))
            batch.request_counts[status] += 1
            batch.request_counts["processing"] -= 1
        batch.processing_status = "ended"
        self._batches[batch.id] = batch
        return batch

    def retrieve(self, batch_id: str) -> _Batch:
        return self._batches[batch_id]

    def results(self, batch_id: str) -> list[_BatchResult]:
        return list(self._batches[batch_id]._results)


class MockAnthropic:
    """Drop-in stand-in for `anthropic.Anthropic`.

    Args:
        responses: list of Message objects returned in order by messages.create.
        router:    callable(request_kwargs, all_calls) -> Message for dynamic replies.
        batch_handler: callable(custom_id, params) -> (status, payload) for batches.
    """

    def __init__(
        self,
        responses: list[Message] | None = None,
        *,
        router: Router | None = None,
        batch_handler: Callable[[str, dict], tuple[str, Any]] | None = None,
        api_key: str | None = "mock-key",
    ):
        self.api_key = api_key
        self.messages = _Messages(responses, router)
        self.messages.batches = _Batches(batch_handler)  # type: ignore[attr-defined]

    @property
    def calls(self) -> list[dict[str, Any]]:
        """Every messages.create request, in order — for asserting on tool_choice etc."""
        return self.messages.calls
