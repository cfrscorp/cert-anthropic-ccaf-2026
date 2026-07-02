"""Deterministic tests for L19 — Multi-Agent Coordinator–Subagent Orchestration.

These lock in the hub-and-spoke contract from Task Statements 1.2 and 1.3:

- a coordinator can only spawn subagents when "Task" is in allowed_tools (1.3);
- subagent prompts carry the COMPLETE prior findings, not a summary reference,
  because subagents do NOT inherit coordinator context (1.3);
- the coordinator dynamically selects a SUBSET of subagents by query complexity
  rather than always running the full pipeline (1.2);
- parallel subagents are spawned by emitting multiple Task calls in ONE response (1.3);
- scope partitioning covers the breadth of a broad topic, guarding against the
  Sample-Question-7 narrow-decomposition failure (1.2).

Run from labs/:  uv run pytest lab-19-multi-agent-orchestration
Validate ref:     LAB_TARGET=solution uv run pytest lab-19-multi-agent-orchestration
"""

from __future__ import annotations

import pytest
from labkit import lab_module
from mock_anthropic import MockAnthropic, message, text_response
from mock_anthropic import ToolUseBlock

orch = lab_module(__file__, "orchestrator")


# --------------------------------------------------------------------------- #
# Fixtures: a small registry of specialised subagents.                         #
# --------------------------------------------------------------------------- #
def make_registry():
    AD = orch.AgentDefinition
    return [
        AD(
            name="web_search",
            description="Searches the web for current news, articles, and online sources.",
            system_prompt="You search the web and return sourced findings.",
            allowed_tools=["web_search"],
        ),
        AD(
            name="doc_analysis",
            description="Analyzes academic papers, PDFs, and research documents.",
            system_prompt="You analyze documents and extract key claims.",
            allowed_tools=["load_document"],
        ),
        AD(
            name="synthesis",
            description="Synthesizes and combines findings from subagents into a comprehensive overview.",
            system_prompt="You synthesize findings into a coherent whole.",
            allowed_tools=["verify_fact"],
        ),
        AD(
            name="report_writer",
            description="Writes comprehensive, cited reports from synthesized findings.",
            system_prompt="You write the final cited report.",
            allowed_tools=[],
        ),
        AD(
            name="fact_checker",
            description="Verifies individual facts, dates, and statistics against sources.",
            system_prompt="You confirm or refute specific factual claims.",
            allowed_tools=["verify_fact"],
        ),
    ]


# --------------------------------------------------------------------------- #
# 1.3 — Task tool gating                                                       #
# --------------------------------------------------------------------------- #
def test_coordinator_can_spawn_requires_task_tool():
    AD = orch.AgentDefinition
    with_task = AD("coordinator", "hub", "sys", allowed_tools=["Task", "Read"])
    without_task = AD("weak", "hub", "sys", allowed_tools=["Read", "Grep"])

    assert orch.coordinator_can_spawn(with_task) is True
    assert orch.coordinator_can_spawn(without_task) is False


# --------------------------------------------------------------------------- #
# 1.3 — Explicit context passing: COMPLETE prior findings, no inheritance      #
# --------------------------------------------------------------------------- #
def test_build_subagent_prompt_embeds_complete_findings_verbatim():
    long_finding = (
        "Global recorded-music revenue reached 28.6 billion USD in 2023, up 10.2 percent "
        "year over year, driven primarily by paid streaming subscriptions."
    )
    findings = [
        {
            "claim": "AI-assisted mastering tools cut production time by roughly 30 percent.",
            "source": "https://example.com/music-ai-report",
            "date": "2024-03-11",
        },
        long_finding,
    ]
    criteria = [
        "Cover music, writing, and film — not only visual arts.",
        "Preserve every source URL and publication date.",
    ]

    prompt = orch.build_subagent_prompt(
        goal="Assess AI's impact on the music industry.",
        prior_findings=findings,
        quality_criteria=criteria,
    )

    # The full finding TEXT is present, not a truncated/summary reference.
    assert long_finding in prompt
    assert "AI-assisted mastering tools cut production time by roughly 30 percent." in prompt
    # Metadata is preserved alongside content (attribution survives the handoff).
    assert "https://example.com/music-ai-report" in prompt
    assert "2024-03-11" in prompt
    # Goal and quality criteria are included (goals, not step-by-step procedure).
    assert "Assess AI's impact on the music industry." in prompt
    for c in criteria:
        assert c in prompt
    # The prompt makes the isolation contract explicit (does not rely on inheritance).
    assert "inherit" in prompt.lower()


# --------------------------------------------------------------------------- #
# 1.2 — Dynamic selection: subset for simple, more for complex (not full)      #
# --------------------------------------------------------------------------- #
def test_select_subagents_scales_with_query_complexity():
    registry = make_registry()

    simple = orch.select_subagents({"text": "What are the latest headlines about AI?"}, registry)
    complex_q = orch.select_subagents(
        {
            "text": (
                "Write a comprehensive, cited report comparing recent news and "
                "academic papers on AI in medicine."
            )
        },
        registry,
    )

    # Simple query routes to a small subset (a single gatherer is enough).
    assert simple == ["web_search"]
    assert len(simple) == 1

    # Complex query pulls in more specialists...
    assert len(complex_q) > len(simple)
    assert {"web_search", "doc_analysis", "synthesis", "report_writer"} <= set(complex_q)
    # ...but selection is still DYNAMIC, not the full pipeline: no verification asked.
    assert "fact_checker" not in complex_q
    assert len(complex_q) < len(registry)


# --------------------------------------------------------------------------- #
# 1.3 — Parallel spawn: multiple Task calls in ONE response                    #
# --------------------------------------------------------------------------- #
def test_spawn_parallel_emits_multiple_task_calls_in_one_turn():
    AD = orch.AgentDefinition
    coordinator = AD("coordinator", "hub", "sys", allowed_tools=["Task"])
    tasks = [
        {"subagent_type": "web_search", "prompt": "Research AI in music."},
        {"subagent_type": "doc_analysis", "prompt": "Analyze papers on AI in film."},
        {"subagent_type": "web_search", "prompt": "Research AI in writing."},
    ]

    blocks = orch.spawn_parallel(coordinator, tasks)

    # More than one Task call, all in a single returned turn.
    assert len(blocks) == 3
    assert all(b["name"] == "Task" for b in blocks)
    assert all(b["type"] == "tool_use" for b in blocks)
    # Each carries its own self-contained prompt and target subagent.
    assert [b["input"]["subagent_type"] for b in blocks] == ["web_search", "doc_analysis", "web_search"]
    assert blocks[0]["input"]["prompt"] == "Research AI in music."
    # tool_use ids are unique so multiple parallel calls don't collide.
    assert len({b["id"] for b in blocks}) == 3


def test_spawn_parallel_requires_task_capable_coordinator():
    AD = orch.AgentDefinition
    weak = AD("weak", "hub", "sys", allowed_tools=["Read"])
    with pytest.raises(ValueError):
        orch.spawn_parallel(weak, [{"subagent_type": "web_search", "prompt": "x"}])


# --------------------------------------------------------------------------- #
# 1.2 — Scope partitioning covers breadth (guards Sample Question 7)           #
# --------------------------------------------------------------------------- #
def test_partition_scope_covers_creative_industries_breadth():
    parts = orch.partition_scope("creative industries", 4)

    assert len(parts) == 4
    # Distinct, non-overlapping subtopics.
    assert len(set(parts)) == 4

    joined = " ".join(parts).lower()
    # The Q7 failure was decomposing into visual arts ONLY. Coverage must span
    # music, writing, and film as well.
    assert "music" in joined
    assert "writing" in joined
    assert "film" in joined
    # And it should NOT collapse into three visual-arts subtasks.
    assert not all("visual" in p.lower() or "art" in p.lower() or "design" in p.lower() for p in parts)


def test_partition_scope_generic_topic_is_distinct_and_covering():
    parts = orch.partition_scope("renewable energy", 5)
    assert len(parts) == 5
    assert len(set(parts)) == 5
    # Every partition is scoped to the topic.
    assert all("renewable energy" in p.lower() for p in parts)


# --------------------------------------------------------------------------- #
# 1.2 / 1.3 — End-to-end demo over the MockAnthropic harness                   #
# --------------------------------------------------------------------------- #
def test_run_coordination_spawns_parallel_and_isolates_context():
    registry = make_registry()
    coordinator = orch.AgentDefinition(
        "coordinator", "hub", "Coordinate the research.", allowed_tools=["Task"]
    )
    full_registry = [coordinator, *registry]

    query = {
        "text": (
            "Write a comprehensive, cited report comparing recent news and "
            "academic papers on AI in medicine."
        )
    }

    context_marker = "PRIOR FINDING: streaming revenue was 28.6B in 2023."

    def router(req, calls):
        # Turn 1: the coordinator call carries the Task tool -> emit parallel Task
        # calls in a SINGLE response (multiple tool_use blocks in one message).
        if req.get("tools"):
            return message(
                blocks=[
                    ToolUseBlock(
                        name="Task",
                        input={
                            "subagent_type": "web_search",
                            "prompt": f"Find recent news on AI in medicine.\n{context_marker}",
                        },
                        id="toolu_a",
                    ),
                    ToolUseBlock(
                        name="Task",
                        input={
                            "subagent_type": "doc_analysis",
                            "prompt": f"Analyze academic papers on AI in medicine.\n{context_marker}",
                        },
                        id="toolu_b",
                    ),
                ],
                stop_reason="tool_use",
            )
        # Subagent turns: each runs with an isolated message list (no coordinator
        # history) — assert the injected context is present in the sole message.
        sole = req["messages"][-1]["content"]
        assert context_marker in sole
        assert len(req["messages"]) == 1  # fresh conversation, nothing inherited
        return text_response("Finding from subagent.")

    client = MockAnthropic(router=router)
    result = orch.run_coordination(client, query, full_registry)

    # One coordinator turn emitted BOTH Task calls (parallel), then 2 subagent runs.
    assert len(result["delegations"]) == 2
    assert len(result["results"]) == 2
    # 1 coordinator call + 2 subagent calls == 3 total messages.create calls.
    assert len(client.calls) == 3
    # The first (coordinator) call advertised the Task tool.
    assert any(t["name"] == "Task" for t in client.calls[0]["tools"])
    # Selection was computed dynamically for observability.
    assert "web_search" in result["selected"]
