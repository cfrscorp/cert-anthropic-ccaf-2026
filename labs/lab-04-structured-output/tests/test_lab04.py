"""Deterministic tests for Lab 04 — Structured Output via tool_use.

Run the learner's work (default):   uv run pytest lab-04-structured-output -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-04-structured-output -q
"""

from __future__ import annotations

import pytest
from labkit import lab_module
from mock_anthropic import MockAnthropic, text_response, tool_use_response

# Load extract.py from starter/ (default) or solution/ (LAB_TARGET=solution).
mod = lab_module(__file__, "extract")


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _properties(tool: dict) -> dict:
    return tool["input_schema"]["properties"]


def _is_nullable(prop: dict) -> bool:
    """A JSON-schema property is nullable when its type list includes 'null'."""
    t = prop.get("type")
    return isinstance(t, list) and "null" in t


# A canonical, well-formed extraction result the mock will "return".
GOOD_INPUT = {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-1001",
    "document_type": "invoice",
    "document_type_detail": None,
    "total_amount": 250.0,
    "currency": "USD",
    "due_date": "2026-08-01",
}


# --------------------------------------------------------------------------- #
# Schema design                                                               #
# --------------------------------------------------------------------------- #
def test_tool_definition_is_well_formed():
    tool = mod.build_extraction_tool()
    assert isinstance(tool, dict)
    assert isinstance(tool.get("name"), str) and tool["name"]
    assert isinstance(tool.get("description"), str) and tool["description"]
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert isinstance(schema.get("properties"), dict) and schema["properties"]
    assert isinstance(schema.get("required"), list) and schema["required"]


def test_schema_has_a_nullable_field():
    """At least one field must allow null so the model returns null vs fabricating."""
    props = _properties(mod.build_extraction_tool())
    nullable = [name for name, p in props.items() if _is_nullable(p)]
    assert nullable, "expected at least one nullable field (type list containing 'null')"


def test_schema_has_enum_with_other():
    """Some field must be an enum that includes an 'other' escape hatch."""
    props = _properties(mod.build_extraction_tool())
    enums_with_other = [
        name
        for name, p in props.items()
        if isinstance(p.get("enum"), list) and "other" in p["enum"]
    ]
    assert enums_with_other, "expected an enum field containing 'other'"


def test_build_returns_independent_copies():
    """Mutating one tool dict must not corrupt the next build."""
    a = mod.build_extraction_tool()
    a["input_schema"]["properties"].clear()
    b = mod.build_extraction_tool()
    assert b["input_schema"]["properties"], "build_extraction_tool must return a copy"


# --------------------------------------------------------------------------- #
# extract(): forwarding and reading the tool_use block                        #
# --------------------------------------------------------------------------- #
def test_extract_forwards_tools_and_forced_tool_choice_by_default():
    tool = mod.build_extraction_tool()
    client = MockAnthropic(responses=[tool_use_response(tool["name"], GOOD_INPUT)])

    result = mod.extract(client, "some invoice text")

    assert result == GOOD_INPUT  # returns the tool_use block's input dict
    assert len(client.calls) == 1
    call = client.calls[0]
    # The extraction tool is forwarded to the API.
    assert call["tools"] == [tool]
    # Default tool_choice forces the extraction tool.
    assert call["tool_choice"] == {"type": "tool", "name": tool["name"]}


def test_extract_forwards_explicit_tool_choice():
    tool = mod.build_extraction_tool()
    client = MockAnthropic(responses=[tool_use_response(tool["name"], GOOD_INPUT)])

    mod.extract(client, "doc", tool_choice="any")

    assert client.calls[0]["tool_choice"] == "any"


def test_extract_passes_through_null_without_fabricating():
    """When a field is genuinely absent, the model returns null and extract keeps it."""
    tool = mod.build_extraction_tool()
    absent = dict(GOOD_INPUT)
    absent["due_date"] = None  # document stated no due date
    client = MockAnthropic(responses=[tool_use_response(tool["name"], absent)])

    result = mod.extract(client, "invoice with no due date")

    assert result["due_date"] is None  # not fabricated / not dropped


def test_extract_returns_none_when_model_returns_only_text():
    """Under tool_choice='auto' the model may answer conversationally."""
    client = MockAnthropic(responses=[text_response("I can help with that.")])
    result = mod.extract(client, "hello", tool_choice="auto")
    assert result is None


# --------------------------------------------------------------------------- #
# pick_tool_choice(): canonical scenarios                                     #
# --------------------------------------------------------------------------- #
def test_pick_tool_choice_unknown_document_type_is_any():
    assert mod.pick_tool_choice("unknown_document_type") == "any"


def test_pick_tool_choice_metadata_first_is_forced():
    assert mod.pick_tool_choice("must_extract_metadata_first") == {
        "type": "tool",
        "name": "extract_metadata",
    }


def test_pick_tool_choice_conversational_is_auto():
    assert mod.pick_tool_choice("conversational_allowed") == "auto"


def test_pick_tool_choice_rejects_unknown_scenario():
    with pytest.raises(ValueError):
        mod.pick_tool_choice("not_a_real_scenario")


# --------------------------------------------------------------------------- #
# Optional semantic check (only runs with ANTHROPIC_API_KEY + -m llm)         #
# --------------------------------------------------------------------------- #
@pytest.mark.llm
def test_schema_descriptions_are_clear():
    from grading import grade, require_llm

    require_llm()
    tool = mod.build_extraction_tool()
    import json

    verdict = grade(
        rubric=(
            "The tool description and field descriptions clearly instruct the "
            "model to return null when information is absent rather than "
            "fabricating values, and clearly explain when to use the enum's "
            "'other' value together with its detail field."
        ),
        submission=json.dumps(tool, indent=2),
    )
    assert verdict["pass"], verdict["reason"]
