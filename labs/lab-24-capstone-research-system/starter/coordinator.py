"""Starter — the coordinator: partition, select, spawn, delegate, run.

Implement Task Statements 1.2 / 1.3 and the Sample Q7/Q8 behaviors. See
README.md (Task B and Task E). The public API must match solution/coordinator.py.
This module is imported, not run as a script.
"""

from __future__ import annotations

import json  # noqa: F401  (useful for serializing prior findings / spawn plans)
from typing import Any

from agents import (  # noqa: F401
    AgentDefinition,
    build_agent_registry,
    record_findings_schema,
    task_tool_schema,
)
from errors import handle_timeout  # noqa: F401
from synthesis import synthesize  # noqa: F401

__all__ = [
    "TOPIC_FACETS",
    "GENERIC_FACETS",
    "expected_facets",
    "partition_scope",
    "repair_coverage",
    "select_subagents",
    "build_subagent_prompt",
    "spawn_parallel",
    "run_subagent",
    "run_research",
]

# Extend this taxonomy: the distinct facets a broad topic must cover (Sample Q7).
TOPIC_FACETS: dict[str, tuple[str, ...]] = {
    "creative": ("visual arts", "music", "writing", "film"),
}

GENERIC_FACETS: tuple[str, ...] = (
    "overview",
    "current state",
    "key challenges",
    "future outlook",
)


def expected_facets(topic: str) -> list[str]:
    """Return the facets a broad topic should cover (Sample Q7)."""
    # TODO: match a keyword in `topic` against TOPIC_FACETS; else GENERIC_FACETS.
    raise NotImplementedError("Implement expected_facets (see README.md).")


def partition_scope(topic: str, *, client: Any = None) -> list[dict[str, Any]]:
    """Partition a broad topic into non-overlapping subtopics that COVER it."""
    # TODO: one partition per expected facet; each dict has facet, subtopic,
    # query, subagent, source_type. Coverage must not collapse to one sub-domain.
    raise NotImplementedError("Implement partition_scope (see README.md).")


def repair_coverage(
    topic: str, partitions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Add partitions for any expected facet a too-narrow proposal missed (Q7)."""
    # TODO: keep existing partitions; append one for each missing expected facet.
    raise NotImplementedError("Implement repair_coverage (see README.md).")


def select_subagents(
    topic: str,
    partitions: list[dict[str, Any]],
    *,
    has_documents: bool = False,
) -> list[str]:
    """Dynamically choose which subagents to invoke (Task 1.2)."""
    # TODO: web_search from partitions; doc_analysis only if has_documents;
    # always append synthesis and report.
    raise NotImplementedError("Implement select_subagents (see README.md).")


def build_subagent_prompt(
    agent_def: AgentDefinition,
    task: dict[str, Any],
    *,
    prior_findings: Any = None,
) -> str:
    """Build a self-contained prompt embedding the COMPLETE prior findings (1.3)."""
    # TODO: include role, system prompt, facet, subtopic, query, and — when
    # prior_findings is given — the FULL findings serialized verbatim (never a
    # summary), delimited so the isolated subagent has complete context.
    raise NotImplementedError("Implement build_subagent_prompt (see README.md).")


def spawn_parallel(
    client: Any,
    tasks: list[dict[str, Any]],
    *,
    coordinator_def: AgentDefinition | None = None,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> list[Any]:
    """Spawn in PARALLEL: ONE coordinator turn emitting multiple Task calls (1.3)."""
    # TODO: make exactly one client.messages.create call with tools=[task schema];
    # return the Task tool_use blocks the coordinator emitted.
    raise NotImplementedError("Implement spawn_parallel (see README.md).")


def run_subagent(
    client: Any,
    agent_def: AgentDefinition,
    task: dict[str, Any],
    *,
    prior_findings: Any = None,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Run one subagent; return findings OR structured error context (Q8)."""
    # TODO: build the prompt, call the client; on TimeoutError/ConnectionError,
    # return structured error context via handle_timeout instead of raising.
    raise NotImplementedError("Implement run_subagent (see README.md).")


def run_research(
    client: Any,
    topic: str,
    *,
    registry: dict[str, AgentDefinition] | None = None,
    documents: list[Any] | None = None,
    content_type: str = "list",
    model: str = "claude-mock",
) -> dict[str, Any]:
    """End-to-end research; proceed with PARTIAL results on failure (Q8-A)."""
    # TODO: partition -> select -> spawn_parallel -> run each subagent ->
    # synthesize; attach errors, partitions, selected_subagents, spawned_tasks.
    raise NotImplementedError("Implement run_research (see README.md).")
