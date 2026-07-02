"""Deterministic tests for Lab 06 — Few-shot Prompting & Explicit Criteria.

Run the learner's work (default):   uv run pytest lab-06-few-shot-and-criteria -q
Validate the reference solution:    LAB_TARGET=solution uv run pytest lab-06-few-shot-and-criteria -q
"""

from __future__ import annotations

import json

import pytest
from labkit import lab_module, lab_root

# Load prompt_builder.py from starter/ (default) or solution/ (LAB_TARGET=solution).
mod = lab_module(__file__, "prompt_builder")

_EXAMPLES_DIR = lab_root(__file__) / "examples"


def _load(name: str) -> list[dict]:
    return json.loads((_EXAMPLES_DIR / name).read_text())


REVIEW_EXAMPLES = _load("review_few_shot.json")
EXTRACTION_EXAMPLES = _load("extraction_few_shot.json")

CRITERIA = [
    "A comment's claimed behavior contradicts the actual code behavior",
    "User-controlled input reaches a query or shell without sanitization",
    "A common code path can raise an unhandled exception on a realistic input",
]

# A vague prompt (Task Statement 4.1 anti-pattern) — no categories to include/exclude.
VAGUE_PROMPT = (
    "Review this pull request. Be conservative and only report high-confidence "
    "findings. Check that the comments are accurate."
)

# A hand-written concrete categorical prompt (no build helper) for an independent check.
CONCRETE_PROMPT = (
    "Report an issue when user input reaches a SQL query without sanitization. "
    "Skip subjective style preferences and naming nits."
)


# --------------------------------------------------------------------------- #
# build_review_prompt: embeds criteria and every few-shot example             #
# --------------------------------------------------------------------------- #
def test_build_embeds_every_criterion():
    prompt = mod.build_review_prompt(CRITERIA, REVIEW_EXAMPLES)
    assert isinstance(prompt, str) and prompt
    for c in CRITERIA:
        assert c in prompt, f"criterion missing from prompt: {c!r}"


def test_build_embeds_every_few_shot_example():
    prompt = mod.build_review_prompt(CRITERIA, REVIEW_EXAMPLES)
    for ex in REVIEW_EXAMPLES:
        assert ex["input"] in prompt, "example input not embedded"
        assert ex["output"] in prompt, "example output not embedded"
        assert ex["why"] in prompt, "example reasoning (why) not embedded"


def test_build_has_report_and_skip_sections():
    prompt = mod.build_review_prompt(CRITERIA, REVIEW_EXAMPLES)
    low = prompt.lower()
    assert "report" in low, "prompt should tell the model what to REPORT"
    assert "skip" in low, "prompt should tell the model what to SKIP"


def test_build_output_is_recognized_as_explicit_criteria():
    prompt = mod.build_review_prompt(CRITERIA, REVIEW_EXAMPLES)
    assert mod.has_explicit_criteria(prompt) is True


def test_build_rejects_too_few_examples():
    with pytest.raises(ValueError):
        mod.build_review_prompt(CRITERIA, REVIEW_EXAMPLES[:1])


def test_build_rejects_empty_criteria():
    with pytest.raises(ValueError):
        mod.build_review_prompt([], REVIEW_EXAMPLES)


# --------------------------------------------------------------------------- #
# has_explicit_criteria: True on concrete, False on vague                     #
# --------------------------------------------------------------------------- #
def test_has_explicit_criteria_true_for_concrete_prompt():
    assert mod.has_explicit_criteria(CONCRETE_PROMPT) is True


def test_has_explicit_criteria_false_for_vague_prompt():
    assert mod.has_explicit_criteria(VAGUE_PROMPT) is False


# --------------------------------------------------------------------------- #
# is_vague_instruction: flags the canonical vague phrases                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "phrase",
    [
        "Be conservative when reviewing.",
        "Only report high-confidence findings.",
        "Use your best judgment.",
        "When in doubt, flag it.",
    ],
)
def test_is_vague_instruction_flags_canonical_hedges(phrase):
    assert mod.is_vague_instruction(phrase) is True


def test_is_vague_instruction_false_for_concrete_criterion():
    concrete = (
        "Report an issue only when a comment's claimed behavior contradicts the "
        "actual code behavior."
    )
    assert mod.is_vague_instruction(concrete) is False


# --------------------------------------------------------------------------- #
# severity_rubric: distinct, concrete levels                                  #
# --------------------------------------------------------------------------- #
def test_severity_rubric_has_distinct_concrete_levels():
    rubric = mod.severity_rubric()
    assert isinstance(rubric, dict)
    assert len(rubric) >= 3, "expected at least three severity levels"
    # Every level carries a concrete code example.
    examples = []
    for level, info in rubric.items():
        assert isinstance(info, dict), f"level {level!r} must map to a dict"
        assert info.get("code_example"), f"level {level!r} needs a concrete code_example"
        examples.append(info["code_example"])
    # Code examples are distinct across levels (no copy-paste placeholders).
    assert len(set(examples)) == len(examples), "code examples must be distinct per level"


# --------------------------------------------------------------------------- #
# examples/ set: an extraction case with varied document structures           #
# --------------------------------------------------------------------------- #
def test_extraction_examples_cover_varied_citation_formats():
    assert 2 <= len(EXTRACTION_EXAMPLES) <= 4
    for ex in EXTRACTION_EXAMPLES:
        for key in ("input", "output", "why"):
            assert ex.get(key), f"extraction example missing {key!r}"
    styles = {json.loads(ex["output"]).get("citation_style") for ex in EXTRACTION_EXAMPLES}
    assert {"inline", "bibliography"} <= styles, (
        "extraction examples should demonstrate both inline and bibliography citations"
    )


# --------------------------------------------------------------------------- #
# Optional semantic check (only runs with ANTHROPIC_API_KEY + -m llm)         #
# --------------------------------------------------------------------------- #
@pytest.mark.llm
def test_built_prompt_yields_consistent_format():
    from grading import grade, require_llm

    require_llm()
    prompt = mod.build_review_prompt(CRITERIA, REVIEW_EXAMPLES)
    verdict = grade(
        rubric=(
            "The submission is a code-review system prompt that would produce "
            "consistently formatted, actionable output. It (1) defines explicit "
            "categorical criteria for which issues to REPORT versus SKIP rather "
            "than vague confidence hedges, (2) specifies a concrete output format "
            "with location, issue, severity, and suggested fix, and (3) includes "
            "few-shot examples that demonstrate that format and the reasoning for "
            "choosing one action over a plausible alternative."
        ),
        submission=prompt,
    )
    assert verdict["pass"], verdict["reason"]
