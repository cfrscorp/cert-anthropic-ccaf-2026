"""Starter — AgentDefinition registry for the multi-agent research system.

Build the hub-and-spoke registry: one coordinator that delegates to specialized
subagents, each with a SCOPED tool set. See README.md (Task A).

Rules you must satisfy (Task Statements 1.2, 1.3, 2.3):
    - The coordinator's allowed_tools MUST include "Task" (the spawn mechanism).
    - Each subagent gets only the tools its role needs.
    - The synthesis agent gets ONLY the scoped `verify_fact` tool (NOT the full
      web-search toolset) — principle of least privilege.

The public API (names, signatures) must match solution/agents.py so the shared
test suite runs against both. This module is imported, not run as a script.
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

TASK_TOOL = "Task"
SUBAGENT_TYPES = ("web_search", "doc_analysis", "synthesis", "report")


@dataclass(frozen=True)
class AgentDefinition:
    """Configuration for one agent (name, description, system prompt, tools)."""

    name: str
    description: str
    system_prompt: str
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    model: str = "claude-mock"


def task_tool_schema() -> dict[str, Any]:
    """Return the schema for the Task spawn tool the coordinator emits."""
    # TODO: return a tool schema named TASK_TOOL with subagent_type + prompt inputs.
    raise NotImplementedError("Implement task_tool_schema (see README.md).")


def record_findings_schema() -> dict[str, Any]:
    """Return the structured-output tool a research subagent uses for findings."""
    # TODO: schema whose `findings` items carry claim, value, excerpt, facet, and
    # a source object (name, url, date) so provenance survives synthesis.
    raise NotImplementedError("Implement record_findings_schema (see README.md).")


def verify_fact_schema() -> dict[str, Any]:
    """Return the scoped verify_fact tool schema for the synthesis agent."""
    # TODO: a NARROW fact-check tool for simple lookups only (Sample Q9).
    raise NotImplementedError("Implement verify_fact_schema (see README.md).")


def build_agent_registry() -> dict[str, AgentDefinition]:
    """Return the hub-and-spoke registry keyed by agent name."""
    # TODO: build coordinator (allowed_tools includes "Task"), web_search,
    # doc_analysis, synthesis (allowed_tools = ("verify_fact",) ONLY), and report.
    raise NotImplementedError("Implement build_agent_registry (see README.md).")


def coordinator_can_spawn(registry: dict[str, AgentDefinition]) -> bool:
    """Return True iff the coordinator has the Task tool in allowed_tools."""
    # TODO: check "Task" in registry["coordinator"].allowed_tools.
    raise NotImplementedError("Implement coordinator_can_spawn (see README.md).")
