"""Structured output via tool_use (Lab 04 reference solution).

Public API (identical in starter/ and solution/):

    build_extraction_tool() -> dict
        Return a valid tool definition whose input_schema is the output schema.

    extract(client, document, *, tool_choice=None) -> dict
        Call client.messages.create with the extraction tool and return the
        structured data from the tool_use block. Default tool_choice forces the
        extraction tool so the call is guaranteed to yield structured output.

    pick_tool_choice(scenario: str) -> object
        Map a canonical scenario name to the appropriate tool_choice value.

Dependency injection: callers pass in the Anthropic client (real or mock) so the
tests can drive this offline with MockAnthropic.
"""

from __future__ import annotations

import copy
from typing import Any

from schema import EXTRACTION_TOOL

__all__ = ["build_extraction_tool", "extract", "pick_tool_choice"]

# Model id is irrelevant to the mock but kept realistic for the live path.
MODEL = "claude-sonnet-5"


def build_extraction_tool() -> dict[str, Any]:
    """Return a fresh copy of the extraction tool definition.

    A deep copy is returned so callers (and tests) can mutate the result without
    corrupting the shared schema module.
    """
    return copy.deepcopy(EXTRACTION_TOOL)


def extract(
    client: Any,
    document: str,
    *,
    tool_choice: Any | None = None,
) -> dict[str, Any] | None:
    """Extract structured data from ``document`` using tool_use.

    Args:
        client: an Anthropic-style client (real SDK or MockAnthropic) exposing
            ``client.messages.create(**kwargs)``.
        document: the raw, unstructured document text to extract from.
        tool_choice: override the tool_choice. Defaults to forcing the extraction
            tool (``{"type": "tool", "name": <tool>}``) so the response is
            guaranteed to be a schema-compliant tool call rather than free text.

    Returns:
        The ``input`` dict of the extraction tool_use block (the structured
        output), or None if the model returned no tool call (only possible with
        ``tool_choice="auto"``).
    """
    tool = build_extraction_tool()
    if tool_choice is None:
        tool_choice = {"type": "tool", "name": tool["name"]}

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[tool],
        tool_choice=tool_choice,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the billing data from the following document by "
                    "calling the extraction tool.\n\n"
                    f"<document>\n{document}\n</document>"
                ),
            }
        ],
    )

    # Prefer the block for our named tool; fall back to any tool_use block (e.g.
    # under tool_choice="any" the model might call a different registered tool).
    blocks = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
    for block in blocks:
        if block.name == tool["name"]:
            return dict(block.input)
    if blocks:
        return dict(blocks[0].input)
    return None  # only reachable with tool_choice="auto" returning plain text


# Canonical scenario -> tool_choice mappings. See Task Statements 2.3 and 4.3.
_SCENARIO_CHOICES: dict[str, Any] = {
    # Many possible extraction schemas and the document type is unknown: force a
    # tool call but let the model pick which schema fits.
    "unknown_document_type": "any",
    # A specific tool must run first (e.g. metadata before enrichment): force it.
    "must_extract_metadata_first": {"type": "tool", "name": "extract_metadata"},
    # The turn may legitimately be a plain conversational reply: let the model
    # decide whether to call a tool at all.
    "conversational_allowed": "auto",
}


def pick_tool_choice(scenario: str) -> Any:
    """Return the appropriate tool_choice for a canonical scenario.

    Scenarios:
        "unknown_document_type"        -> "any"
        "must_extract_metadata_first"  -> {"type": "tool", "name": "extract_metadata"}
        "conversational_allowed"       -> "auto"

    Raises:
        ValueError: if ``scenario`` is not one of the canonical scenarios.
    """
    try:
        choice = _SCENARIO_CHOICES[scenario]
    except KeyError:
        raise ValueError(
            f"Unknown scenario {scenario!r}; expected one of "
            f"{sorted(_SCENARIO_CHOICES)}"
        ) from None
    # Return a copy of dict choices so callers can't mutate the mapping.
    return copy.deepcopy(choice) if isinstance(choice, dict) else choice
