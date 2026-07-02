"""Reference solution: coordinator–subagent orchestration primitives.

This module models the *hub-and-spoke* multi-agent pattern from Task Statements
1.2 and 1.3. A single coordinator agent owns all routing, decomposition,
delegation, and aggregation; subagents run with **isolated context** (they never
inherit the coordinator's conversation history) and are spawned via the ``Task``
tool.

Public API (identical in ``starter/`` and ``solution/``):

    AgentDefinition                         # dataclass: name/description/system_prompt/allowed_tools
    coordinator_can_spawn(coordinator)      # -> bool: "Task" in allowed_tools
    build_subagent_prompt(goal, prior_findings, quality_criteria)  # -> str (embeds COMPLETE findings)
    select_subagents(query, registry)       # -> list[str]: dynamic subset by complexity
    spawn_parallel(coordinator, tasks)      # -> list[dict]: Task tool_use blocks for ONE turn
    partition_scope(topic, n)               # -> list[str]: distinct, covering subtopics
    run_coordination(client, query, registry)  # -> dict: end-to-end demo over MockAnthropic

Everything here is a plain importable module (no shell entrypoint), so the
user's runnable-script conventions do not apply; behaviour is documented in
docstrings and exercised by ``tests/test_lab19.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "AgentDefinition",
    "TASK_TOOL",
    "coordinator_can_spawn",
    "build_subagent_prompt",
    "select_subagents",
    "spawn_parallel",
    "partition_scope",
    "run_coordination",
]


# --------------------------------------------------------------------------- #
# Agent configuration                                                          #
# --------------------------------------------------------------------------- #
@dataclass
class AgentDefinition:
    """Configuration for one agent (coordinator OR subagent).

    Mirrors the Agent SDK ``AgentDefinition``: a ``name``, a ``description`` the
    coordinator uses to decide when to delegate, a ``system_prompt`` that scopes
    the agent's role, and ``allowed_tools`` (tool restrictions). A coordinator
    must include ``"Task"`` in ``allowed_tools`` to be able to spawn subagents.
    """

    name: str
    description: str
    system_prompt: str = ""
    allowed_tools: list[str] = field(default_factory=list)


# The Task tool is the mechanism for spawning subagents. Its schema forces the
# coordinator to pass a *self-contained* prompt (isolated context, no inheritance).
TASK_TOOL: dict[str, Any] = {
    "name": "Task",
    "description": (
        "Spawn a subagent with an ISOLATED context. The subagent does not inherit "
        "this conversation, so `prompt` must contain every piece of context it "
        "needs. Emit multiple Task calls in ONE response to run subagents in parallel."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "subagent_type": {"type": "string", "description": "Which registered subagent to run."},
            "prompt": {"type": "string", "description": "Self-contained prompt with all needed context."},
        },
        "required": ["subagent_type", "prompt"],
    },
}


def coordinator_can_spawn(coordinator: AgentDefinition) -> bool:
    """True iff the coordinator is allowed to invoke the ``Task`` tool.

    Spawning subagents requires ``"Task"`` in ``allowed_tools``; without it the
    coordinator can only answer directly and cannot delegate.
    """
    return "Task" in (coordinator.allowed_tools or [])


# --------------------------------------------------------------------------- #
# Context passing (1.3): embed COMPLETE prior findings — no inheritance        #
# --------------------------------------------------------------------------- #
def _render_finding(index: int, finding: Any) -> str:
    """Render one prior finding *in full*, keeping content separate from metadata.

    Dict findings are rendered key-by-key (so ``source``/``date``/``page`` stay
    attached to their ``claim``/``excerpt``); anything else is stringified
    verbatim. Nothing is summarised or truncated — the whole point is that the
    subagent receives the complete upstream output.
    """
    header = f"[{index}]"
    if isinstance(finding, dict):
        lines = [header]
        for key, value in finding.items():
            lines.append(f"    {key}: {value}")
        return "\n".join(lines)
    return f"{header} {finding}"


def build_subagent_prompt(
    goal: str,
    prior_findings: list[Any],
    quality_criteria: list[str],
) -> str:
    """Build a self-contained subagent prompt.

    Because subagents have isolated context, the prompt must carry everything:
    the ``goal``, the **complete** ``prior_findings`` (verbatim, not a summary
    reference), and the ``quality_criteria``. Per Task Statement 1.3 the criteria
    describe *goals and quality bars*, not step-by-step procedure — the subagent
    decides how to achieve them.
    """
    findings = list(prior_findings or [])
    if findings:
        rendered = "\n".join(_render_finding(i, f) for i, f in enumerate(findings, start=1))
    else:
        rendered = "(none provided)"

    criteria = list(quality_criteria or [])
    criteria_block = "\n".join(f"- {c}" for c in criteria) if criteria else "- (none specified)"

    return (
        "=== SUBAGENT TASK ===\n"
        f"GOAL:\n{goal}\n\n"
        "CONTEXT — COMPLETE PRIOR FINDINGS\n"
        "(You run with an ISOLATED context and do NOT inherit the coordinator's "
        "conversation history. Everything you need is included below, verbatim.)\n"
        f"{rendered}\n\n"
        "QUALITY CRITERIA (meet these; choose your own approach — this is not a "
        "step-by-step script):\n"
        f"{criteria_block}\n"
    )


# --------------------------------------------------------------------------- #
# Dynamic subagent selection (1.2): pick a subset by query complexity          #
# --------------------------------------------------------------------------- #
# Query trigger words -> the capability they imply.
_CAPABILITY_TRIGGERS: dict[str, set[str]] = {
    "web_search": {"web", "search", "news", "current", "latest", "online", "recent", "internet"},
    "doc_analysis": {"document", "paper", "pdf", "study", "academic", "analyze", "analysis", "literature", "publication"},
    "synthesis": {"synthesize", "combine", "compare", "comprehensive", "integrate", "overview"},
    "report": {"report", "cited", "citation", "deliverable", "brief", "write-up"},
    "fact_check": {"verify", "fact-check", "fact check", "confirm", "validate"},
}


def _capabilities_for_query(query: dict) -> set[str]:
    """Infer which capabilities a query needs (its 'complexity fingerprint')."""
    explicit = query.get("capabilities")
    if explicit:
        return set(explicit)

    text = str(query.get("text", "")).lower()
    needed: set[str] = set()
    for cap, triggers in _CAPABILITY_TRIGGERS.items():
        if any(t in text for t in triggers):
            needed.add(cap)

    gatherers = {"web_search", "doc_analysis"} & needed
    if not gatherers:
        # Every query needs at least one information source.
        needed.add("web_search")
        gatherers = {"web_search"}
    if len(gatherers) >= 2:
        # Multiple sources must be reconciled -> synthesis is required.
        needed.add("synthesis")
    return needed


def _agent_capability(agent: AgentDefinition) -> str | None:
    """Classify a registered agent into a capability from its name + description."""
    text = f"{agent.name} {agent.description}".lower()
    best: str | None = None
    best_score = 0
    for cap, triggers in _CAPABILITY_TRIGGERS.items():
        score = 2 if cap in text or cap.replace("_", " ") in text else 0
        score += sum(1 for t in triggers if t in text)
        if score > best_score:
            best, best_score = cap, score
    return best if best_score > 0 else None


def select_subagents(query: dict, registry: list[AgentDefinition]) -> list[str]:
    """Dynamically choose which subagents to invoke for ``query``.

    This is the coordinator's routing decision (Task Statement 1.2): analyse the
    query's requirements and pick only the relevant subset, rather than always
    running the full pipeline. Returns subagent *names* in registry order.
    """
    needed = _capabilities_for_query(query)
    selected: list[str] = []
    for agent in registry:
        cap = _agent_capability(agent)
        if cap in needed and agent.name not in selected:
            selected.append(agent.name)
    return selected


# --------------------------------------------------------------------------- #
# Parallel spawning (1.3): multiple Task calls in ONE response                 #
# --------------------------------------------------------------------------- #
def _normalize_task(index: int, task: Any) -> dict[str, Any]:
    """Coerce a task spec into a Task tool_use ``input`` dict."""
    if isinstance(task, dict):
        subagent = task.get("subagent_type") or task.get("subagent") or task.get("name")
        prompt = task.get("prompt") or task.get("description")
        if not subagent or prompt is None:
            raise ValueError(
                f"task #{index} must provide a subagent name and a prompt; got {task!r}"
            )
        extra = {k: v for k, v in task.items() if k not in {"subagent_type", "subagent", "name", "prompt", "description"}}
        return {"subagent_type": subagent, "prompt": prompt, **extra}
    raise ValueError(f"task #{index} must be a dict, got {type(task).__name__}")


def spawn_parallel(coordinator: AgentDefinition, tasks: list[Any]) -> list[dict[str, Any]]:
    """Build the Task tool_use blocks for spawning ``tasks`` **in parallel**.

    Parallelism comes from emitting *all* of these blocks in a SINGLE coordinator
    response (one assistant turn with N tool_use blocks), rather than one Task
    call per turn. The returned list is exactly that turn's ``content``.

    Raises ``ValueError`` if the coordinator cannot spawn (no ``"Task"`` tool) or
    if ``tasks`` is empty.
    """
    if not coordinator_can_spawn(coordinator):
        raise ValueError(
            "coordinator cannot spawn subagents: 'Task' is not in allowed_tools"
        )
    if not tasks:
        raise ValueError("spawn_parallel requires at least one task")

    blocks: list[dict[str, Any]] = []
    for i, task in enumerate(tasks):
        blocks.append(
            {
                "type": "tool_use",
                "name": "Task",
                "id": f"toolu_task_{i}",
                "input": _normalize_task(i, task),
            }
        )
    return blocks


# --------------------------------------------------------------------------- #
# Scope partitioning (1.2): distinct, non-overlapping, COVERING subtopics      #
# --------------------------------------------------------------------------- #
# Curated decompositions that cover the breadth of a broad topic. The creative
# industries entry deliberately spans music/writing/film/visual arts/etc. to
# guard against the Sample-Question-7 failure (decomposing into visual arts only).
_TOPIC_PARTITIONS: dict[str, list[str]] = {
    "creative industries": [
        "music and audio production",
        "writing and publishing",
        "film and video production",
        "visual arts and design",
        "video game development",
        "performing arts and theater",
        "advertising and marketing creative",
    ],
}

_GENERIC_FACETS: list[str] = [
    "history and background of {t}",
    "current state and key players in {t}",
    "economic and market impact of {t}",
    "technology and methods in {t}",
    "social and ethical implications of {t}",
    "future trends and outlook for {t}",
    "regulation and policy around {t}",
    "criticism and controversies in {t}",
]


def partition_scope(topic: str, n: int) -> list[str]:
    """Split a broad ``topic`` into ``n`` distinct, non-overlapping subtopics.

    The subtopics are chosen to *cover* the breadth of the topic, not drill into
    one corner of it. This directly counters the coordinator failure in Sample
    Question 7, where "creative industries" was decomposed into three visual-arts
    subtasks and music/writing/film were never researched.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")

    key = topic.strip().lower()
    base = _TOPIC_PARTITIONS.get(key)
    if base is not None:
        parts = list(base)
    else:
        parts = [f.format(t=topic.strip()) for f in _GENERIC_FACETS]

    chosen: list[str] = parts[:n]
    # If more partitions were requested than we have, pad with generic facets,
    # then numbered aspects — always keeping entries distinct.
    if len(chosen) < n:
        for facet in _GENERIC_FACETS:
            if len(chosen) >= n:
                break
            cand = facet.format(t=topic.strip())
            if cand not in chosen:
                chosen.append(cand)
        i = 1
        while len(chosen) < n:
            cand = f"{topic.strip()} — aspect {i}"
            if cand not in chosen:
                chosen.append(cand)
            i += 1

    # De-duplicate while preserving order (belt and braces).
    seen: set[str] = set()
    out: list[str] = []
    for c in chosen:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


# --------------------------------------------------------------------------- #
# End-to-end demo over the MockAnthropic harness (optional)                    #
# --------------------------------------------------------------------------- #
def _default_coordinator() -> AgentDefinition:
    return AgentDefinition(
        name="coordinator",
        description="Hub-and-spoke coordinator: decomposes, delegates, aggregates.",
        system_prompt=(
            "You are the coordinator. Decompose the query, delegate to the right "
            "subagents via the Task tool (include ALL context in each prompt — they "
            "do not inherit your history), then aggregate their findings."
        ),
        allowed_tools=["Task"],
    )


def _system_for(name: str, subagents: list[AgentDefinition]) -> str:
    for agent in subagents:
        if agent.name == name:
            return agent.system_prompt
    return ""


def run_coordination(
    client: Any,
    query: dict,
    registry: list[AgentDefinition],
    *,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Drive one hub-and-spoke coordination pass over an injected client.

    Flow (all inter-agent communication routed through the coordinator):

    1. Pick a coordinator (any registry agent with ``"Task"``, else a default).
    2. Turn 1: the coordinator emits parallel ``Task`` calls in a SINGLE response.
    3. Each subagent runs with a FRESH message list (isolated context — the only
       thing it sees is the self-contained prompt from the Task call).
    4. Return the delegations and per-subagent results for aggregation.

    ``client`` is injected (a ``MockAnthropic`` in tests). Assert on
    ``client.calls`` to verify parallel emission and context isolation.
    """
    coordinator = next((a for a in registry if coordinator_can_spawn(a)), None)
    subagents = [a for a in registry if a is not coordinator]
    if coordinator is None:
        coordinator = _default_coordinator()

    selected = select_subagents(query, subagents)

    # Turn 1 — the coordinator decides delegation and emits parallel Task calls.
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=coordinator.system_prompt,
        messages=[{"role": "user", "content": query.get("text", "")}],
        tools=[TASK_TOOL],
    )
    task_blocks = resp.tool_use_blocks()

    # Fan out — each subagent runs in isolation (fresh conversation).
    results: list[dict[str, Any]] = []
    for block in task_blocks:
        stype = block.input.get("subagent_type")
        sub_prompt = block.input.get("prompt", "")
        sub_resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_system_for(stype, subagents),
            messages=[{"role": "user", "content": sub_prompt}],
        )
        results.append({"subagent": stype, "prompt": sub_prompt, "text": sub_resp.text})

    return {
        "coordinator": coordinator.name,
        "selected": selected,
        "delegations": [dict(block.input) for block in task_blocks],
        "results": results,
    }
