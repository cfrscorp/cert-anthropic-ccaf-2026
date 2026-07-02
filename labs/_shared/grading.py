"""Optional LLM-as-judge grading for labs whose output is genuinely semantic.

Deterministic pytest is always preferred. Use this ONLY when correctness depends
on meaning that a string/structural assertion cannot capture (e.g. "does this
tool description actually disambiguate two similar tools?").

Tests that use it must be marked ``@pytest.mark.llm`` so that the default run
(``pytest -m 'not llm'``) stays fully deterministic and offline. When no
``ANTHROPIC_API_KEY`` is set, ``grade`` raises ``pytest.skip`` via
``require_llm()``.

    import pytest
    from grading import grade, require_llm

    @pytest.mark.llm
    def test_descriptions_disambiguate():
        require_llm()
        verdict = grade(
            rubric="The two tool descriptions make it unambiguous which to call "
                   "for an order-status question vs a customer-profile question.",
            submission=open("solution/tools.json").read(),
        )
        assert verdict["pass"], verdict["reason"]
"""

from __future__ import annotations

import json
import os
from typing import Any

__all__ = ["llm_available", "require_llm", "grade", "GRADER_MODEL"]

GRADER_MODEL = "claude-sonnet-5"

_GRADER_SYSTEM = (
    "You are a strict grader for a certification lab. You are given a RUBRIC and a "
    "SUBMISSION. Judge only whether the submission satisfies the rubric. Be objective "
    "and conservative. Respond by calling the `report` tool."
)

_REPORT_TOOL = {
    "name": "report",
    "description": "Report the grading verdict.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pass": {"type": "boolean", "description": "True iff the rubric is satisfied."},
            "score": {"type": "number", "description": "0.0-1.0 quality score."},
            "reason": {"type": "string", "description": "One or two sentences justifying the verdict."},
        },
        "required": ["pass", "score", "reason"],
    },
}


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def require_llm() -> None:
    """Skip the current test if no API key is configured."""
    if not llm_available():
        import pytest

        pytest.skip("ANTHROPIC_API_KEY not set; skipping LLM-graded test.")


def grade(rubric: str, submission: str, *, model: str = GRADER_MODEL) -> dict[str, Any]:
    """Grade a submission against a rubric using a real Claude call.

    Returns a dict: {"pass": bool, "score": float, "reason": str}.
    Requires ANTHROPIC_API_KEY (call ``require_llm()`` first in tests).
    """
    import anthropic  # imported lazily so offline runs never need the package

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        system=_GRADER_SYSTEM,
        tools=[_REPORT_TOOL],
        tool_choice={"type": "tool", "name": "report"},
        messages=[
            {
                "role": "user",
                "content": f"RUBRIC:\n{rubric}\n\nSUBMISSION:\n{submission}",
            }
        ],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise RuntimeError(f"Grader did not return a tool_use block: {json.dumps(resp.model_dump())}")
