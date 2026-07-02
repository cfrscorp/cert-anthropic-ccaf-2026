"""Starter scaffold: coordinator–subagent orchestration primitives.

Implement the hub-and-spoke multi-agent pattern from Task Statements 1.2 and 1.3.
A single coordinator owns routing/decomposition/delegation/aggregation; subagents
run with ISOLATED context (they never inherit the coordinator's history) and are
spawned via the ``Task`` tool.

Fill in every function below so the tests in ``tests/test_lab19.py`` pass. Keep
the public API identical to ``solution/orchestrator.py``:

    AgentDefinition, coordinator_can_spawn, build_subagent_prompt,
    select_subagents, spawn_parallel, partition_scope, run_coordination

The ``AgentDefinition`` dataclass and the ``TASK_TOOL`` schema are provided so
your signatures line up; the function bodies are yours to write.

Run the tests from the ``labs/`` directory:
    uv run pytest lab-19-multi-agent-orchestration
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


@dataclass
class AgentDefinition:
    """Configuration for one agent (coordinator OR subagent).

    Mirrors the Agent SDK ``AgentDefinition``: a ``name``, a ``description`` the
    coordinator uses to decide when to delegate, a ``system_prompt`` scoping the
    role, and ``allowed_tools`` (tool restrictions). A coordinator must include
    ``"Task"`` in ``allowed_tools`` to spawn subagents.
    """

    name: str
    description: str
    system_prompt: str = ""
    allowed_tools: list[str] = field(default_factory=list)


# The Task tool is the mechanism for spawning subagents. Provided for you.
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
            "subagent_type": {"type": "string"},
            "prompt": {"type": "string"},
        },
        "required": ["subagent_type", "prompt"],
    },
}


def coordinator_can_spawn(coordinator: AgentDefinition) -> bool:
    """Return True iff the coordinator may invoke the ``Task`` tool.

    Hint: spawning subagents requires ``"Task"`` in ``allowed_tools``.
    """
    # TODO: return whether "Task" is in coordinator.allowed_tools.
    raise NotImplementedError("Implement coordinator_can_spawn (see README.md).")


def build_subagent_prompt(
    goal: str,
    prior_findings: list[Any],
    quality_criteria: list[str],
) -> str:
    """Build a self-contained subagent prompt.

    Subagents have isolated context, so embed EVERYTHING: the goal, the COMPLETE
    prior findings (verbatim — not a summary reference), and the quality criteria.
    Criteria should express goals/quality bars, not a step-by-step procedure.

    Hint: render dict findings key-by-key so metadata (source/date/page) stays
    attached to content (claim/excerpt); include str findings verbatim.
    """
    # TODO: assemble goal + full prior_findings + quality_criteria into one string.
    raise NotImplementedError("Implement build_subagent_prompt (see README.md).")


def select_subagents(query: dict, registry: list[AgentDefinition]) -> list[str]:
    """Dynamically choose which subagents to invoke for ``query``.

    Analyse the query's requirements and pick only the relevant subset — do NOT
    always run the full pipeline. Return subagent names (in registry order).

    Hint: infer needed capabilities from the query, classify each registered
    agent by its name/description, and keep the matches.
    """
    # TODO: return the subset of registry names whose capability the query needs.
    raise NotImplementedError("Implement select_subagents (see README.md).")


def spawn_parallel(coordinator: AgentDefinition, tasks: list[Any]) -> list[dict[str, Any]]:
    """Build the Task tool_use blocks for spawning ``tasks`` in PARALLEL.

    Return a list of tool_use blocks (one per task) intended to be emitted in a
    SINGLE coordinator response — that single multi-block turn is what makes the
    subagents run in parallel.

    Raise ``ValueError`` if the coordinator cannot spawn or ``tasks`` is empty.
    """
    # TODO: guard on coordinator_can_spawn and non-empty tasks, then build one
    #       {"type":"tool_use","name":"Task",...} block per task.
    raise NotImplementedError("Implement spawn_parallel (see README.md).")


def partition_scope(topic: str, n: int) -> list[str]:
    """Split a broad ``topic`` into ``n`` distinct, non-overlapping subtopics that
    COVER its breadth (not one narrow corner).

    This counters the Sample-Question-7 failure: decomposing "creative industries"
    into three visual-arts subtasks so music/writing/film are never researched.
    """
    # TODO: return n distinct subtopics that span the topic's breadth.
    raise NotImplementedError("Implement partition_scope (see README.md).")


def run_coordination(
    client: Any,
    query: dict,
    registry: list[AgentDefinition],
    *,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Drive one hub-and-spoke coordination pass over an injected ``client``.

    1. Pick a coordinator (a registry agent with "Task", else a default).
    2. Turn 1: coordinator emits parallel Task calls in a SINGLE response.
    3. Run each subagent with a FRESH message list (isolated context).
    4. Return the delegations and per-subagent results.
    """
    # TODO: implement the coordination flow described above using client.messages.create.
    raise NotImplementedError("Implement run_coordination (see README.md).")
