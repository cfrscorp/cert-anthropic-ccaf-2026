"""Structured output via tool_use (Lab 04 STARTER — implement the TODOs).

Public API (must match solution/):

    build_extraction_tool() -> dict
    extract(client, document, *, tool_choice=None) -> dict | None
    pick_tool_choice(scenario: str) -> object

Callers inject the Anthropic client (real SDK or MockAnthropic) so tests run
offline. Do not construct a client inside these functions.
"""

from __future__ import annotations

from typing import Any

from schema import EXTRACTION_TOOL  # noqa: F401  (use it in build_extraction_tool)

__all__ = ["build_extraction_tool", "extract", "pick_tool_choice"]

MODEL = "claude-sonnet-5"


def build_extraction_tool() -> dict[str, Any]:
    """Return a fresh copy of the extraction tool definition."""
    # TODO: return a deep copy of EXTRACTION_TOOL so callers can't mutate the
    # shared schema module.
    raise NotImplementedError("build_extraction_tool: return a copy of EXTRACTION_TOOL")


def extract(
    client: Any,
    document: str,
    *,
    tool_choice: Any | None = None,
) -> dict[str, Any] | None:
    """Extract structured data from ``document`` using tool_use.

    Steps:
      1. Build the extraction tool.
      2. If tool_choice is None, DEFAULT to forcing the extraction tool
         ({"type": "tool", "name": <tool name>}) so the reply is guaranteed to be
         a schema-compliant tool call, not free text.
      3. Call client.messages.create(model=..., max_tokens=..., tools=[tool],
         tool_choice=tool_choice, messages=[...]).
      4. Find the tool_use block for the extraction tool and return its .input
         as a plain dict. Return None if there is no tool_use block.
    """
    # TODO: implement per the docstring.
    raise NotImplementedError("extract: call messages.create and return the tool_use input")


def pick_tool_choice(scenario: str) -> Any:
    """Map a canonical scenario name to the appropriate tool_choice value.

        "unknown_document_type"        -> "any"
        "must_extract_metadata_first"  -> {"type": "tool", "name": "extract_metadata"}
        "conversational_allowed"       -> "auto"

    Raise ValueError for any other scenario.
    """
    # TODO: implement the mapping.
    raise NotImplementedError("pick_tool_choice: map scenario -> tool_choice")
