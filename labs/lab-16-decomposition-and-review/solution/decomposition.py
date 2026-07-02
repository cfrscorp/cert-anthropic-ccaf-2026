"""Reference solution for L16 — Task Decomposition & Multi-pass Review.

Two exam ideas drive this module:

* Task Statement 1.6 — pick FIXED sequential pipelines (prompt chaining) when the
  full set of subtasks is knowable up front (predictable multi-aspect reviews),
  and DYNAMIC adaptive decomposition when subtasks must be generated from what
  you discover at each step (open-ended investigation such as "add comprehensive
  tests to a legacy codebase").
* Task Statement 4.6 — split a large multi-file review into one local pass per
  file plus a single cross-file integration pass (avoids attention dilution and
  contradictory findings); prefer an INDEPENDENT review instance over
  self-review (the generator retains its reasoning and is less likely to question
  itself); and route findings by self-reported confidence for calibrated human
  review.

This is exactly the Sample Question 12 situation: a 14-file PR reviewed in a
single pass gives inconsistent depth and contradictory feedback. The fix is not
a bigger model, not smaller PRs, and not consensus-of-3 — it is splitting into
per-file passes plus one integration pass (see ``review_scenario.md``).

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

__all__ = [
    "choose_decomposition",
    "plan_review_passes",
    "is_independent_review",
    "route_by_confidence",
    "independent_second_pass",
    "DEFAULT_MODEL",
]

# Model id passed through to the injected client. The MockAnthropic client used
# in tests ignores it; it exists so real callers can override it.
DEFAULT_MODEL = "claude-sonnet-4-5"


# --------------------------------------------------------------------------- #
# 1. Choose the decomposition strategy (Task Statement 1.6).
# --------------------------------------------------------------------------- #
# The deciding question is simple: can you enumerate the full set of subtasks
# BEFORE you start? If yes, a fixed sequential pipeline (prompt chaining) is the
# right, cheaper, more predictable choice. If the subtasks only become knowable
# as you discover structure and dependencies, you need dynamic decomposition.

_PROMPT_CHAINING_TYPES = frozenset(
    {
        "multi_file_review",
        "code_review",
        "review",
        "multi_aspect_review",
        "extraction_pipeline",
        "translation_pipeline",
    }
)
_DYNAMIC_TYPES = frozenset(
    {
        "investigation",
        "add_tests",
        "legacy_test_generation",
        "exploration",
        "open_ended",
        "refactor_legacy",
    }
)

_DYNAMIC_KEYWORDS = (
    "comprehensive test",
    "add test",
    "legacy",
    "investigate",
    "investigation",
    "explore",
    "open-ended",
    "open ended",
    "figure out",
    "map the structure",
    "as dependencies are discovered",
    "high-impact",
    "unknown structure",
    "no existing test",
)
_CHAINING_KEYWORDS = (
    "review each",
    "analyze each file",
    "each file",
    "per-file",
    "cross-file integration",
    "integration pass",
    "multi-aspect",
    "predictable",
    "fixed pipeline",
    "sequential pipeline",
    "known set of",
)


def choose_decomposition(task: dict) -> str:
    """Return ``"prompt_chaining"`` or ``"dynamic"`` for ``task``.

    ``"prompt_chaining"`` — predictable, multi-aspect work whose subtasks are
    knowable up front (e.g. review each file, then a cross-file integration pass).

    ``"dynamic"`` — open-ended investigation whose subtasks are generated from
    intermediate findings (e.g. "add comprehensive tests to a legacy codebase":
    map structure, find high-impact areas, adapt as dependencies surface).
    """
    if not isinstance(task, dict):
        raise TypeError(f"task must be a dict, got {type(task).__name__}")

    # 1. An explicit flag is authoritative.
    open_ended = task.get("open_ended")
    if open_ended is True:
        return "dynamic"
    if open_ended is False:
        return "prompt_chaining"

    # 2. A known task type dispatches directly.
    kind = str(task.get("type") or task.get("kind") or "").strip().lower()
    if kind in _DYNAMIC_TYPES:
        return "dynamic"
    if kind in _PROMPT_CHAINING_TYPES:
        return "prompt_chaining"

    # 3. Keyword signals in the free-text fields.
    text = " ".join(
        str(task.get(k, "")) for k in ("goal", "description", "title", "task", "prompt")
    ).lower()
    dynamic_hits = sum(kw in text for kw in _DYNAMIC_KEYWORDS)
    chaining_hits = sum(kw in text for kw in _CHAINING_KEYWORDS)
    if dynamic_hits > chaining_hits:
        return "dynamic"
    if chaining_hits > dynamic_hits:
        return "prompt_chaining"

    # 4. Tie-break: a bounded, known file list is a predictable pipeline;
    #    otherwise default to the safer adaptive plan.
    if task.get("files") and task.get("subtasks_known_upfront", True):
        return "prompt_chaining"
    return "dynamic"


# --------------------------------------------------------------------------- #
# 2. Plan multi-pass review passes (Task Statements 1.6 + 4.6).
# --------------------------------------------------------------------------- #
def plan_review_passes(files: list[str]) -> list[dict]:
    """One LOCAL pass per file + EXACTLY ONE cross-file integration pass.

    For N files the plan has N + 1 entries. Each local pass looks only at a
    single file (consistent depth, no attention dilution). The final integration
    pass looks across every file for data-flow issues and contradictions that a
    per-file pass structurally cannot see.
    """
    if not isinstance(files, (list, tuple)):
        raise TypeError(f"files must be a list, got {type(files).__name__}")
    files = list(files)
    if not files:
        raise ValueError("need at least one file to plan a review")

    passes: list[dict] = []
    for index, name in enumerate(files, start=1):
        passes.append(
            {
                "pass": index,
                "kind": "local",
                "scope": "file",
                "file": name,
                "files": [name],
                "focus": (
                    "Local issues within a single file: bugs, edge cases, "
                    "error handling, and file-local conventions."
                ),
            }
        )
    passes.append(
        {
            "pass": len(files) + 1,
            "kind": "integration",
            "scope": "cross_file",
            "file": None,
            "files": list(files),
            "focus": (
                "Cross-file data flow, interface/contract mismatches, and "
                "contradictory findings across files."
            ),
        }
    )
    return passes


# --------------------------------------------------------------------------- #
# 3. Independent review vs self-review (Task Statement 4.6).
# --------------------------------------------------------------------------- #
def is_independent_review(review_context: dict) -> bool:
    """Return True when the reviewer is INDEPENDENT of the generator.

    A model retains the reasoning context it used while generating code, so a
    self-review in the same session is less likely to question its own decisions.
    An independent instance (fresh session, no generation reasoning) catches
    subtle issues that self-review and extended thinking miss.

    Precedence:
      1. explicit ``shares_reasoning_context`` flag,
      2. reviewer vs generator session ids (same session -> self-review),
      3. whether the reviewer was handed the generation reasoning trace.
    """
    if not isinstance(review_context, dict):
        raise TypeError(
            f"review_context must be a dict, got {type(review_context).__name__}"
        )

    shares = review_context.get("shares_reasoning_context")
    if shares is None:
        generator = review_context.get("generator_session_id")
        reviewer = review_context.get("reviewer_session_id")
        if generator is not None and reviewer is not None:
            shares = generator == reviewer
        else:
            # If the reviewer was handed the generator's reasoning/chain of
            # thought, it is effectively a self-review even in a new session.
            shares = bool(review_context.get("includes_generation_reasoning", False))

    return not bool(shares)


# --------------------------------------------------------------------------- #
# 4. Route findings by self-reported confidence (Task Statement 4.6 + 5.5).
# --------------------------------------------------------------------------- #
def route_by_confidence(findings: list[dict], threshold: float) -> dict:
    """Split ``findings`` into auto-apply vs human-review by ``confidence``.

    A finding with ``confidence >= threshold`` routes to ``"auto"``. Anything
    below the threshold — or missing a confidence value entirely — routes to
    ``"human_review"`` (fail safe toward human attention).
    """
    if not isinstance(findings, (list, tuple)):
        raise TypeError(f"findings must be a list, got {type(findings).__name__}")

    auto: list[dict] = []
    human_review: list[dict] = []
    for finding in findings:
        confidence = finding.get("confidence")
        if isinstance(confidence, (int, float)) and confidence >= threshold:
            auto.append(finding)
        else:
            human_review.append(finding)

    return {
        "auto": auto,
        "human_review": human_review,
        "threshold": threshold,
    }


# --------------------------------------------------------------------------- #
# 5. Drive an independent second-instance review (optional; DI via client).
# --------------------------------------------------------------------------- #
_REPORT_FINDING_TOOL = {
    "name": "report_finding",
    "description": (
        "Report one issue found while reviewing the code. Call once per distinct "
        "issue; include a calibrated confidence in [0, 1]."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "line": {"type": "integer"},
            "issue": {"type": "string"},
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            },
            "confidence": {"type": "number"},
        },
        "required": ["file", "issue", "severity", "confidence"],
    },
}

_REVIEW_PROMPT = (
    "You are an INDEPENDENT reviewer. You did not write this code and you have "
    "no prior context about how it was produced. Review the file below for bugs, "
    "edge cases, and correctness issues. Report each issue via the "
    "report_finding tool.\n\nFile: {file}\n\n```\n{code}\n```"
)


def independent_second_pass(client, review_target: dict, *, model: str = DEFAULT_MODEL) -> list[dict]:
    """Run a review with a fresh Claude instance and return its findings.

    ``client`` is injected so tests can supply a mock; critically it carries none
    of the generator's conversation history, which is what makes the review
    independent (4.6). ``review_target`` is ``{"file": ..., "code": ...}``.
    Returns a list of finding dicts parsed from the model's tool calls.
    """
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        tools=[_REPORT_FINDING_TOOL],
        tool_choice={"type": "any"},
        messages=[
            {
                "role": "user",
                "content": _REVIEW_PROMPT.format(
                    file=review_target.get("file", "<unknown>"),
                    code=review_target.get("code", ""),
                ),
            }
        ],
    )

    findings: list[dict] = []
    for block in response.tool_use_blocks():
        if block.name == "report_finding":
            findings.append(dict(block.input))
    return findings
