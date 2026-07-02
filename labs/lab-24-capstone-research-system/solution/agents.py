"""Reference solution — AgentDefinition registry for the multi-agent research system.

Scenario 3 (Multi-Agent Research System), Task Statements 1.2 and 1.3.

A **hub-and-spoke** system: one coordinator delegates to specialized subagents.
The coordinator owns all inter-agent routing and error handling; subagents run
with *isolated context* and only the tools their role needs.

Key exam ideas baked into this registry:

- The coordinator's ``allowed_tools`` MUST include ``"Task"`` — that is the
  mechanism for spawning subagents (Task Statement 1.3). Without it the
  coordinator cannot delegate at all.
- Each subagent gets a **scoped** tool set (Task Statement 2.3 / principle of
  least privilege). The synthesis agent does NOT get the full web-search toolset;
  it gets one narrow cross-role tool, ``verify_fact``, for the high-frequency 85%
  simple-lookup case (Sample Question 9), while complex verifications route back
  through the coordinator.
- System prompts state *goals and quality criteria*, not step-by-step procedures,
  so subagents stay adaptable (Task Statement 1.3 skill).

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "AgentDefinition",
    "TASK_TOOL",
    "SUBAGENT_TYPES",
    "build_agent_registry",
    "coordinator_can_spawn",
    "task_tool_schema",
    "record_findings_schema",
    "verify_fact_schema",
]

# The Task tool is the spawn mechanism. A coordinator can only delegate to
# subagents if this name is present in its allowed_tools (Task Statement 1.3).
TASK_TOOL = "Task"

# The four specialized subagents in Scenario 3.
SUBAGENT_TYPES = ("web_search", "doc_analysis", "synthesis", "report")


@dataclass(frozen=True)
class AgentDefinition:
    """Configuration for one agent in the hub-and-spoke system.

    Mirrors the Agent SDK ``AgentDefinition`` shape used on the exam: a name, a
    natural-language description (used for selection), a system prompt stating
    goals/criteria, and a restricted tool set.
    """

    name: str
    description: str
    system_prompt: str
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    model: str = "claude-mock"


def task_tool_schema() -> dict[str, Any]:
    """Schema for the Task spawn tool the coordinator emits to launch subagents.

    Emitting several of these tool_use blocks in a *single* coordinator turn is
    how subagents run in parallel (Task Statement 1.3).
    """
    return {
        "name": TASK_TOOL,
        "description": (
            "Spawn a specialized subagent to work an assigned subtopic. The "
            "subagent runs with ISOLATED context: it does not inherit the "
            "coordinator's history, so `prompt` must contain everything it needs, "
            "including any prior findings it must build on. Emit multiple Task "
            "calls in one turn to run subagents in parallel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subagent_type": {
                    "type": "string",
                    "enum": list(SUBAGENT_TYPES),
                    "description": "Which specialized subagent to spawn.",
                },
                "description": {
                    "type": "string",
                    "description": "Short label for the delegated task.",
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Complete, self-contained instructions and context for the "
                        "subagent (goals + full prior findings, not a summary)."
                    ),
                },
            },
            "required": ["subagent_type", "prompt"],
        },
    }


def record_findings_schema() -> dict[str, Any]:
    """Structured-output tool a research subagent uses to return findings.

    Separating content from metadata (source URL, name, date) here is what lets
    downstream synthesis preserve provenance (Task Statements 5.1 / 5.6).
    """
    return {
        "name": "record_findings",
        "description": (
            "Return research findings as structured claims. Each claim MUST carry "
            "its own source (name, url, publication date) so attribution survives "
            "synthesis. Include a `metric` when the claim reports a statistic so "
            "conflicting values across sources can be detected and preserved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string"},
                            "metric": {"type": ["string", "null"]},
                            "value": {"type": ["string", "null"]},
                            "excerpt": {"type": "string"},
                            "facet": {"type": "string"},
                            "source": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "url": {"type": "string"},
                                    "date": {"type": "string"},
                                },
                                "required": ["name", "date"],
                            },
                        },
                        "required": ["claim", "excerpt", "source"],
                    },
                }
            },
            "required": ["findings"],
        },
    }


def verify_fact_schema() -> dict[str, Any]:
    """Scoped fact-check tool for the synthesis agent (Sample Question 9).

    Deliberately narrow: it is for simple lookups (a date, a name, a single
    statistic) that make up ~85% of verifications. Anything requiring deeper,
    multi-source investigation is routed back through the coordinator to the
    web_search subagent — the synthesis agent is NOT given the full search
    toolset (principle of least privilege, Task Statement 2.3).
    """
    return {
        "name": "verify_fact",
        "description": (
            "Verify a SIMPLE factual claim (a date, a name, or a single "
            "statistic) against a trusted index. Use ONLY for quick lookups. Do "
            "NOT use for interpretive, causal, methodological, or multi-source "
            "questions — return control to the coordinator so the web_search "
            "subagent can investigate those."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "verified": {"type": "boolean"},
                "value": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["claim"],
        },
    }


def build_agent_registry() -> dict[str, AgentDefinition]:
    """Return the hub-and-spoke agent registry.

    - ``coordinator`` — owns delegation; ``allowed_tools`` includes ``"Task"``.
    - ``web_search``  — external search only.
    - ``doc_analysis``— document loading/extraction only.
    - ``synthesis``   — merges findings; gets ONLY the scoped ``verify_fact``
      cross-role tool (not the full search toolset).
    - ``report``      — renders the final report; no research tools.
    """
    return {
        "coordinator": AgentDefinition(
            name="coordinator",
            description=(
                "Hub agent. Partitions a broad topic into non-overlapping "
                "subtopics that fully cover it, dynamically selects which "
                "subagents to invoke, spawns them in parallel via Task, routes "
                "all inter-agent communication, handles errors, and re-delegates "
                "to close coverage gaps."
            ),
            system_prompt=(
                "You are the coordinator of a research system. GOALS: (1) Partition "
                "the topic into subtopics that COVER the whole topic, not just one "
                "familiar corner of it — enumerate the distinct domains a "
                "well-informed reader would expect. (2) Spawn subagents in PARALLEL "
                "by emitting multiple Task calls in a single turn. (3) Pass each "
                "subagent the COMPLETE prior findings it needs directly in its "
                "prompt; subagents do not inherit your context. (4) On a subagent "
                "failure, use its structured error context to decide whether to "
                "retry, reroute, or proceed with partial results and annotate the "
                "coverage gap. State goals and quality criteria, not step-by-step "
                "procedures."
            ),
            allowed_tools=(TASK_TOOL,),
        ),
        "web_search": AgentDefinition(
            name="web_search",
            description="Searches the web for sources relevant to an assigned subtopic.",
            system_prompt=(
                "You research one assigned subtopic via web search. Return "
                "structured claims via record_findings; every claim carries its "
                "source name, URL, and publication date. Report valid empty "
                "results distinctly from access failures."
            ),
            allowed_tools=("web_search", "record_findings"),
        ),
        "doc_analysis": AgentDefinition(
            name="doc_analysis",
            description="Loads and analyzes documents for an assigned subtopic.",
            system_prompt=(
                "You analyze provided documents for one assigned subtopic. Return "
                "structured claims via record_findings with source name, page/date, "
                "and excerpts. Include conflicting values explicitly and annotate "
                "them; let the coordinator reconcile."
            ),
            allowed_tools=("load_document", "extract_data_points", "record_findings"),
        ),
        "synthesis": AgentDefinition(
            name="synthesis",
            description=(
                "Merges findings from other subagents into a coherent, cited whole, "
                "preserving claim-to-source provenance and annotating conflicts."
            ),
            system_prompt=(
                "You synthesize findings passed to you in full. PRESERVE each "
                "claim's source through the merge. When sources disagree on a "
                "statistic, KEEP BOTH values with attribution and dates rather than "
                "choosing one. Use the verify_fact tool ONLY for simple lookups "
                "(dates, names, single statistics); for anything interpretive or "
                "multi-source, hand back to the coordinator."
            ),
            # Scoped cross-role tool ONLY — not the full search toolset.
            allowed_tools=("verify_fact",),
        ),
        "report": AgentDefinition(
            name="report",
            description="Renders the synthesized findings into a final, typed report.",
            system_prompt=(
                "You render the report. Distinguish well-established findings from "
                "contested ones, surface coverage gaps, and render each content "
                "type appropriately (statistics as tables, news as prose, technical "
                "findings as lists)."
            ),
            allowed_tools=(),
        ),
    }


def coordinator_can_spawn(registry: dict[str, AgentDefinition]) -> bool:
    """True iff the coordinator is configured to spawn subagents.

    The Task tool must be in the coordinator's allowed_tools (Task Statement 1.3).
    """
    coordinator = registry.get("coordinator")
    return bool(coordinator and TASK_TOOL in coordinator.allowed_tools)
