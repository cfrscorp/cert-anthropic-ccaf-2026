"""Reference solution — the coordinator: partition, select, spawn, delegate, run.

Task Statements 1.2 and 1.3, and Sample Question 7.

The coordinator is the hub. Its jobs:

- :func:`partition_scope` — decompose a BROAD topic into non-overlapping
  subtopics that COVER it. Sample Q7's failure was decomposing "creative
  industries" into only visual-arts subtasks (digital art, graphic design,
  photography), silently dropping music, writing, and film. The fix is a
  decomposition anchored to the topic's real breadth (Task 1.2 skill: partition to
  minimize duplication AND maximize coverage). :func:`repair_coverage` shows the
  iterative-refinement move that rescues a too-narrow proposal.
- :func:`select_subagents` — dynamically pick which subagents to invoke rather
  than always running the full pipeline (Task 1.2 skill).
- :func:`build_subagent_prompt` — embed the COMPLETE prior findings in the
  subagent's prompt; subagents run with isolated context (Task 1.3).
- :func:`spawn_parallel` — emit multiple Task calls in a SINGLE turn (Task 1.3).
- :func:`run_subagent` / :func:`run_research` — drive the whole thing, turning a
  subagent timeout into structured error context and proceeding with partial
  results + coverage gaps (Task 5.3, Sample Q8).

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

import json
from typing import Any

from agents import (
    AgentDefinition,
    build_agent_registry,
    record_findings_schema,
    task_tool_schema,
)
from errors import handle_timeout
from synthesis import synthesize

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

# Domain taxonomy: the distinct facets a broad topic must cover. Keyed by a
# keyword found in the topic. This is what stops the Sample Q7 failure — a broad
# topic is decomposed across ALL its major domains, not one familiar corner.
TOPIC_FACETS: dict[str, tuple[str, ...]] = {
    "creative": ("visual arts", "music", "writing", "film"),
    "healthcare": ("diagnosis", "treatment", "operations", "patient outcomes"),
    "education": ("k-12", "higher education", "assessment", "accessibility"),
}

# Fallback facets for topics not in the taxonomy — still broad, never single-corner.
GENERIC_FACETS: tuple[str, ...] = (
    "overview",
    "current state",
    "key challenges",
    "future outlook",
)


def expected_facets(topic: str) -> list[str]:
    """Return the facets a broad ``topic`` should cover (Sample Q7)."""
    text = topic.lower()
    for keyword, facets in TOPIC_FACETS.items():
        if keyword in text:
            return list(facets)
    return list(GENERIC_FACETS)


def _partition_for(topic: str, facet: str) -> dict[str, Any]:
    """Build one non-overlapping partition (subtopic) for a facet."""
    return {
        "facet": facet,
        "subtopic": f"{facet} within {topic}",
        "query": f"{topic} — {facet}",
        "subagent": "web_search",
        "source_type": "web",
    }


def partition_scope(topic: str, *, client: Any = None) -> list[dict[str, Any]]:
    """Partition a broad topic into non-overlapping subtopics that cover it.

    Coverage is anchored to :func:`expected_facets`, so a topic like "impact of AI
    on creative industries" is decomposed across visual arts, music, writing, and
    film — never collapsed to a single sub-domain (the Sample Q7 root cause).

    ``client`` is accepted for parity with an LLM-driven coordinator; the
    reference decomposition is deterministic so coverage is guaranteed and tests
    are offline.
    """
    facets = expected_facets(topic)
    return [_partition_for(topic, facet) for facet in facets]


def repair_coverage(
    topic: str, partitions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Add partitions for any expected facet a (too-narrow) proposal missed.

    This is the iterative-refinement move for Sample Q7: given a coordinator
    proposal that only covers, say, digital art / graphic design / photography,
    detect that music, writing, and film are missing and append partitions for
    them. Existing partitions are preserved; only gaps are filled.
    """
    covered = {p.get("facet") for p in partitions}
    repaired = list(partitions)
    for facet in expected_facets(topic):
        if facet not in covered:
            repaired.append(_partition_for(topic, facet))
    return repaired


def select_subagents(
    topic: str,
    partitions: list[dict[str, Any]],
    *,
    has_documents: bool = False,
) -> list[str]:
    """Dynamically choose which subagents to invoke (Task 1.2 skill).

    Not every query needs the full pipeline. Research subagents are selected from
    what the partitions actually require (web_search always; doc_analysis only
    when documents are in scope); synthesis and report always run to combine and
    render.
    """
    research = {p.get("subagent", "web_search") for p in partitions}
    selected = [a for a in ("web_search", "doc_analysis") if a in research]
    if has_documents and "doc_analysis" not in selected:
        selected.append("doc_analysis")
    selected += ["synthesis", "report"]
    return selected


def build_subagent_prompt(
    agent_def: AgentDefinition,
    task: dict[str, Any],
    *,
    prior_findings: Any = None,
) -> str:
    """Build a self-contained subagent prompt embedding COMPLETE prior findings.

    Subagents do not inherit the coordinator's context (Task 1.3), so everything
    the subagent needs goes here — including the FULL prior findings, serialized
    verbatim, never summarized. Summarizing here is how provenance and detail get
    lost downstream.
    """
    lines = [
        f"SUBAGENT ROLE: {agent_def.name}",
        agent_def.system_prompt,
        f"ASSIGNED FACET: {task['facet']}",
        f"SUBTOPIC: {task['subtopic']}",
        f"TASK QUERY: {task['query']}",
        "Return findings via record_findings; every claim carries its source "
        "(name, url, publication date).",
    ]
    if prior_findings is not None and prior_findings != []:
        if isinstance(prior_findings, str):
            serialized = prior_findings
        else:
            serialized = json.dumps(prior_findings, indent=2, sort_keys=True)
        lines.append(
            "--- PRIOR FINDINGS (complete context — do NOT summarize; you do not "
            "inherit the coordinator's memory) ---"
        )
        lines.append(serialized)
        lines.append("--- END PRIOR FINDINGS ---")
    return "\n".join(lines)


def spawn_parallel(
    client: Any,
    tasks: list[dict[str, Any]],
    *,
    coordinator_def: AgentDefinition | None = None,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> list[Any]:
    """Spawn subagents in PARALLEL: one coordinator turn, multiple Task calls.

    Parallelism comes from emitting several Task tool_use blocks in a SINGLE
    coordinator response (Task 1.3) — not from separate turns. This makes exactly
    one ``client.messages.create`` call and returns the Task blocks the
    coordinator emitted.
    """
    if coordinator_def is None:
        coordinator_def = build_agent_registry()["coordinator"]

    plan = "SPAWN PLAN: dispatch these subagent tasks in parallel:\n" + json.dumps(
        tasks, sort_keys=True
    )
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": coordinator_def.system_prompt},
            {"role": "user", "content": plan},
        ],
        tools=[task_tool_schema()],
    )
    return [b for b in resp.tool_use_blocks() if b.name == "Task"]


def run_subagent(
    client: Any,
    agent_def: AgentDefinition,
    task: dict[str, Any],
    *,
    prior_findings: Any = None,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Run one subagent, returning findings or STRUCTURED error context.

    A timeout (surfaced as ``TimeoutError``/``ConnectionError`` from the injected
    client) is caught locally and converted to structured error context via
    :func:`handle_timeout` — never swallowed as empty-success (Q8-C) and never
    allowed to kill the workflow (Q8-D).
    """
    prompt = build_subagent_prompt(agent_def, task, prior_findings=prior_findings)
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=[record_findings_schema()],
        )
    except (TimeoutError, ConnectionError):
        return {
            "ok": False,
            "facet": task["facet"],
            "subagent": agent_def.name,
            "error": handle_timeout(
                task["query"],
                subagent=agent_def.name,
                facet=task["facet"],
                partial_results=[],
            ),
        }

    blocks = [b for b in resp.tool_use_blocks() if b.name == "record_findings"]
    findings = blocks[0].input.get("findings", []) if blocks else []
    return {
        "ok": True,
        "facet": task["facet"],
        "subagent": agent_def.name,
        "findings": findings,
    }


def run_research(
    client: Any,
    topic: str,
    *,
    registry: dict[str, AgentDefinition] | None = None,
    documents: list[Any] | None = None,
    content_type: str = "list",
    model: str = "claude-mock",
) -> dict[str, Any]:
    """End-to-end research: partition -> select -> spawn -> run -> synthesize.

    Ties the whole system together and, crucially, proceeds with PARTIAL results
    when a subagent fails: failed facets become coverage gaps in the report while
    successful ones are synthesized normally (Task 5.3 / Sample Q8-A).
    """
    registry = registry or build_agent_registry()
    partitions = partition_scope(topic)
    selected = select_subagents(topic, partitions, has_documents=bool(documents))

    # Spawn in parallel: one coordinator turn emitting multiple Task calls.
    task_blocks = spawn_parallel(
        client, partitions, coordinator_def=registry["coordinator"], model=model
    )

    finding_lists: list[list[dict[str, Any]]] = []
    errors: list[dict[str, Any]] = []
    for partition in partitions:
        agent_def = registry.get(partition["subagent"], registry["web_search"])
        result = run_subagent(client, agent_def, partition, model=model)
        if result["ok"]:
            finding_lists.append(result["findings"])
        else:
            errors.append(result["error"])

    facets = [p["facet"] for p in partitions]
    report = synthesize(
        topic,
        finding_lists,
        facets=facets,
        errors=errors,
        content_type=content_type,
    )
    report["errors"] = errors
    report["partitions"] = partitions
    report["selected_subagents"] = selected
    report["spawned_tasks"] = len(task_blocks)
    return report
