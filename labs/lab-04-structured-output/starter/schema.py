"""Extraction tool definition for Lab 04 (STARTER — complete the TODOs).

The tool's ``input_schema`` IS the output schema. When Claude calls this tool,
the JSON it produces for the tool's input is guaranteed to be syntactically valid
and schema-shaped, and you read the structured data out of the tool_use block.

Your job: finish INPUT_SCHEMA so it demonstrates all four design techniques from
Task Statement 4.3:

  1. required vs optional fields
  2. nullable fields (type allows "null") so the model returns null instead of
     fabricating a value when the info is absent
  3. an enum field that includes "other"
  4. a paired free-text "detail" field for the "other" case

Reminder: a strict schema removes JSON *syntax* errors but NOT *semantic* errors
(e.g. line items not summing to the total). That is a later validation step.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "TOOL_NAME",
    "TOOL_DESCRIPTION",
    "DOCUMENT_TYPES",
    "INPUT_SCHEMA",
    "EXTRACTION_TOOL",
]

TOOL_NAME = "extract_invoice"

TOOL_DESCRIPTION = (
    "Extract structured billing data from an unstructured invoice or receipt. "
    # TODO: describe the null-when-absent rule so the model does not fabricate.
)

# TODO: define a closed category set that INCLUDES an "other" escape hatch.
DOCUMENT_TYPES: list[str] = []  # e.g. ["invoice", "receipt", ..., "other"]

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "vendor_name": {
            "type": "string",
            "description": "Legal or trading name of the party issuing the document.",
        },
        "total_amount": {
            "type": "number",
            "description": "The grand total stated on the document.",
        },
        # TODO: add a document_type field: {"type": "string", "enum": DOCUMENT_TYPES}.
        # TODO: add a NULLABLE due_date field, e.g. {"type": ["string", "null"], ...}.
        # TODO: add a NULLABLE document_type_detail field for the "other" case.
        # TODO: add at least one OPTIONAL field (not listed in "required" below).
    },
    # TODO: list the fields that must always be present. Include nullable fields
    # here (so the model always addresses them) but leave optional fields out.
    "required": [],
}

EXTRACTION_TOOL: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "input_schema": INPUT_SCHEMA,
}
