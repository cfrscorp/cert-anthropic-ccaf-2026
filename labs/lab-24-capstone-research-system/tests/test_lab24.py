"""Deterministic tests for L24 — Capstone: Multi-Agent Research System.

These lock in the integrative behaviors from Scenario 3 / Exercise 4 and the
correct answers to Sample Questions 7, 8, and 9:

- Q7: the coordinator partitions a BROAD topic across all its domains (music,
  writing, film — not only visual arts), and can repair a too-narrow proposal.
- Q8: a subagent timeout yields STRUCTURED error context and the pipeline
  proceeds with partial results + a coverage gap.
- Q9: the synthesis agent has a SCOPED verify_fact tool for simple lookups while
  complex verifications route back through the coordinator.

Plus the Task 5.6 provenance rules: merge preserves each claim's source, and
conflicting statistics are kept with attribution + dates rather than resolved.

Run from labs/:  uv run pytest lab-24-capstone-research-system
Validate ref:    LAB_TARGET=solution uv run pytest lab-24-capstone-research-system
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from labkit import lab_module
from mock_anthropic import (
    MockAnthropic,
    ToolUseBlock,
    message,
    text_response,
    tool_use_response,
)

agents = lab_module(__file__, "agents")
errors = lab_module(__file__, "errors")
synthesis = lab_module(__file__, "synthesis")
coordinator = lab_module(__file__, "coordinator")

TOPIC = "impact of AI on creative industries"
SOURCES = json.loads(
    (Path(__file__).resolve().parent.parent / "sources.json").read_text()
)


# --------------------------------------------------------------------------- #
# agents.py — hub-and-spoke registry, Task tool, scoped tools                  #
# --------------------------------------------------------------------------- #
def test_coordinator_has_task_in_allowed_tools():
    """Task Statement 1.3: a coordinator can only spawn subagents if it has Task."""
    registry = agents.build_agent_registry()
    assert "Task" in registry["coordinator"].allowed_tools
    assert agents.coordinator_can_spawn(registry) is True


def test_subagent_tools_are_scoped():
    """Task 2.3: synthesis gets ONLY the scoped verify_fact tool, not full search."""
    registry = agents.build_agent_registry()
    synth = registry["synthesis"]
    assert "verify_fact" in synth.allowed_tools
    assert "web_search" not in synth.allowed_tools
    # web_search stays in its lane too.
    assert "web_search" in registry["web_search"].allowed_tools
    assert "verify_fact" not in registry["web_search"].allowed_tools


# --------------------------------------------------------------------------- #
# coordinator.py — partition (Sample Q7), select, prompt, parallel spawn       #
# --------------------------------------------------------------------------- #
def test_partition_scope_covers_all_creative_facets():
    """Sample Q7: broad decomposition must include music, writing, film."""
    partitions = coordinator.partition_scope(TOPIC)
    facets = {p["facet"] for p in partitions}
    # The exact failure from Q7 was covering only visual arts.
    assert {"music", "writing", "film"} <= facets
    assert "visual arts" in facets
    # Non-overlapping: one partition per facet.
    assert len(facets) == len(partitions)
    assert len(partitions) >= 4


def test_repair_coverage_rescues_narrow_decomposition():
    """Sample Q7: a visual-arts-only proposal is repaired to full coverage."""
    narrow = [
        {"facet": "digital art", "subtopic": "", "query": "", "subagent": "web_search"},
        {"facet": "graphic design", "subtopic": "", "query": "", "subagent": "web_search"},
        {"facet": "photography", "subtopic": "", "query": "", "subagent": "web_search"},
    ]
    repaired = coordinator.repair_coverage(TOPIC, narrow)
    facets = {p["facet"] for p in repaired}
    assert {"music", "writing", "film"} <= facets
    # Original partitions are preserved, not discarded.
    assert {"digital art", "graphic design", "photography"} <= facets


def test_select_subagents_is_dynamic():
    """Task 1.2: pick subagents by need; doc_analysis only when documents exist."""
    partitions = coordinator.partition_scope(TOPIC)
    without_docs = coordinator.select_subagents(TOPIC, partitions, has_documents=False)
    with_docs = coordinator.select_subagents(TOPIC, partitions, has_documents=True)

    assert "web_search" in without_docs
    assert "doc_analysis" not in without_docs
    assert "doc_analysis" in with_docs
    # Synthesis and report always run to combine and render.
    for pipeline in (without_docs, with_docs):
        assert "synthesis" in pipeline and "report" in pipeline


def test_build_subagent_prompt_embeds_full_prior_findings():
    """Task 1.3: the COMPLETE prior findings are embedded verbatim, not summarized."""
    registry = agents.build_agent_registry()
    task = {
        "facet": "music",
        "subtopic": "music within " + TOPIC,
        "query": TOPIC + " — music",
        "subagent": "web_search",
    }
    prior = SOURCES["facet_findings"]["visual arts"]
    prompt = coordinator.build_subagent_prompt(
        registry["synthesis"], task, prior_findings=prior
    )

    # The entire prior-findings payload appears verbatim (serialized in full).
    expected = json.dumps(prior, indent=2, sort_keys=True)
    assert expected in prompt
    # Query + facet are present so the isolated subagent has full context.
    assert "ASSIGNED FACET: music" in prompt
    assert task["query"] in prompt
    # A unique excerpt from the prior findings survives (no summarization).
    assert "concept boards" in prompt


def test_spawn_parallel_emits_multiple_tasks_in_one_turn():
    """Task 1.3: parallelism = multiple Task calls in a SINGLE coordinator turn."""

    def router(req, calls):
        assert "SPAWN PLAN" in req["messages"][-1]["content"]
        blocks = [
            ToolUseBlock(name="Task", input={"subagent_type": "web_search", "prompt": "a"}, id="t1"),
            ToolUseBlock(name="Task", input={"subagent_type": "web_search", "prompt": "b"}, id="t2"),
            ToolUseBlock(name="Task", input={"subagent_type": "doc_analysis", "prompt": "c"}, id="t3"),
        ]
        return message(blocks, stop_reason="tool_use")

    client = MockAnthropic(router=router)
    tasks = coordinator.partition_scope(TOPIC)
    task_blocks = coordinator.spawn_parallel(client, tasks)

    # More than one Task, all emitted in exactly ONE model call.
    assert len(task_blocks) > 1
    assert len(client.calls) == 1
    tool_names = {t["name"] for t in client.calls[0]["tools"]}
    assert "Task" in tool_names


# --------------------------------------------------------------------------- #
# errors.py — structured error context (Sample Q8)                             #
# --------------------------------------------------------------------------- #
def test_handle_timeout_builds_structured_error_context():
    """Sample Q8-A: failure type, attempted query, partial results, alternatives."""
    err = errors.handle_timeout(
        "impact of AI on creative industries — film",
        subagent="web_search",
        facet="film",
        partial_results=[],
    )
    assert err["isError"] is True
    assert err["failure_type"] == "timeout"
    assert err["attempted_query"] == "impact of AI on creative industries — film"
    assert err["partial_results"] == []
    assert len(err["alternatives"]) >= 1  # concrete recovery options for the coordinator
    assert err["facet"] == "film"


def test_classify_result_distinguishes_failure_from_empty():
    """Sample Q8-C anti-pattern guard: access_failure != empty_success."""
    assert errors.classify_result({"isError": True}) == "access_failure"
    assert errors.classify_result(None) == "access_failure"
    assert errors.classify_result({"findings": []}) == "empty_success"
    assert errors.classify_result([]) == "empty_success"
    assert errors.classify_result({"findings": [{"claim": "x"}]}) == "results"


# --------------------------------------------------------------------------- #
# synthesis.py — provenance, conflicts, typed rendering (Task 5.6)             #
# --------------------------------------------------------------------------- #
def test_merge_claims_preserves_provenance():
    """Task 5.6: every merged claim retains its own source."""
    visual = SOURCES["facet_findings"]["visual arts"]
    music = SOURCES["facet_findings"]["music"]
    merged = synthesis.merge_claims([visual, music])

    assert len(merged) == len(visual) + len(music)
    assert all("source" in c and c["source"].get("name") for c in merged)
    names = {c["source"]["name"] for c in merged}
    assert {"Creative Industry Council", "Global Arts Foundation"} <= names


def test_merge_claims_rejects_unsourced_claim():
    """A claim missing provenance must not be merged silently."""
    with pytest.raises(ValueError):
        synthesis.merge_claims([[{"claim": "no source here", "value": "1"}]])


def test_annotate_conflict_keeps_both_values_with_dates():
    """Task 5.6: conflicting stats are kept with attribution + dates, not resolved."""
    conflicting = SOURCES["conflicting_claims"]
    conflicts = synthesis.annotate_conflict(conflicting)

    assert len(conflicts) == 1
    obs = conflicts[0]["observations"]
    values = {o["value"] for o in obs}
    assert values == {"45%", "62%"}  # BOTH kept — neither dropped
    dates = {o["date"] for o in obs}
    assert dates == {"2023-09-01", "2024-08-01"}
    # Both sources attributed.
    assert {o["source"] for o in obs} == {
        "Creative Industry Council",
        "Global Arts Foundation",
    }
    # The annotation flags the temporal span so dates aren't read as contradiction.
    assert "2023-09-01" in conflicts[0]["note"]


def test_render_by_type_differs_by_content_type():
    """Task 5.6: statistics->table, news->prose, technical->list."""
    items = SOURCES["facet_findings"]["visual arts"]
    table = synthesis.render_by_type(items, "table")
    prose = synthesis.render_by_type(items, "prose")
    listing = synthesis.render_by_type(items, "list")

    assert "|" in table and "Source" in table  # markdown table
    assert "|" not in prose  # prose has no table pipes
    assert listing.lstrip().startswith("-")  # bulleted list


# --------------------------------------------------------------------------- #
# synthesis.py — scoped verify_fact path (Sample Q9)                           #
# --------------------------------------------------------------------------- #
def test_classify_verification_simple_vs_complex():
    assert synthesis.classify_verification("The survey was published in 2023") == "simple"
    assert synthesis.classify_verification("Jane Doe led the study") == "simple"
    assert (
        synthesis.classify_verification(
            "whether the methodology accounts for selection bias"
        )
        == "complex"
    )


def test_verify_simple_uses_scoped_verify_fact_tool():
    """Sample Q9-A: simple lookups use the scoped verify_fact tool, one call."""
    client = MockAnthropic(
        responses=[
            tool_use_response(
                "verify_fact",
                {"claim": "published in 2023", "verified": True, "value": "2023"},
            )
        ]
    )
    result = synthesis.verify(client, "The survey was published in 2023")

    assert result["verified_via"] == "verify_fact"
    assert len(client.calls) == 1
    call = client.calls[0]
    assert {t["name"] for t in call["tools"]} == {"verify_fact"}
    # Forced tool selection guarantees the scoped tool runs.
    assert call["tool_choice"] == {"type": "tool", "name": "verify_fact"}


def test_verify_complex_routes_to_coordinator_without_calling_verify_fact():
    """Sample Q9-A: complex verifications route back through the coordinator."""
    client = MockAnthropic(responses=[])  # must NOT be called
    routed = {}

    def coordinator_cb(claim):
        routed["claim"] = claim
        return {"handled_by": "coordinator"}

    result = synthesis.verify(
        client,
        "whether the reported growth is causal or coincidental",
        coordinator=coordinator_cb,
    )

    assert result["route"] == "coordinator"
    assert result["result"] == {"handled_by": "coordinator"}
    assert routed["claim"] == "whether the reported growth is causal or coincidental"
    # The scoped tool was never invoked for a complex case.
    assert len(client.calls) == 0


# --------------------------------------------------------------------------- #
# coordinator.py — end-to-end run_research with a timeout (integrative)        #
# --------------------------------------------------------------------------- #
def _research_router(timeout_facet="film"):
    """Router simulating spawn + four subagents; `timeout_facet` times out."""
    facet_findings = SOURCES["facet_findings"]

    def router(req, calls):
        content = req["messages"][-1]["content"]
        if "SPAWN PLAN" in content:
            tasks = json.loads(content.split("\n", 1)[1])
            blocks = [
                ToolUseBlock(
                    name="Task",
                    input={"subagent_type": t["subagent"], "prompt": t["query"]},
                    id=f"task_{i}",
                )
                for i, t in enumerate(tasks)
            ]
            return message(blocks, stop_reason="tool_use")
        # A subagent turn: dispatch by assigned facet.
        for facet, findings in facet_findings.items():
            if f"ASSIGNED FACET: {facet}" in content:
                if facet == timeout_facet:
                    raise TimeoutError(f"{facet} search timed out")
                return tool_use_response("record_findings", {"findings": findings})
        return text_response("no findings")

    return router


def test_run_research_proceeds_with_partial_results_and_gap():
    """Integrative: timeout -> structured error + coverage gap, rest synthesized."""
    client = MockAnthropic(router=_research_router(timeout_facet="film"))
    report = coordinator.run_research(client, TOPIC)

    # Parallel spawn happened (multiple Task calls in the spawn turn).
    assert report["spawned_tasks"] > 1

    # The film timeout became STRUCTURED error context (Sample Q8-A).
    film_errors = [e for e in report["errors"] if e["facet"] == "film"]
    assert len(film_errors) == 1
    assert film_errors[0]["failure_type"] == "timeout"
    assert film_errors[0]["attempted_query"]
    assert film_errors[0]["alternatives"]

    # The pipeline PROCEEDED with partial results (Q8: not C, not D).
    covered = {c["status"]: [] for c in report["coverage"]}
    for c in report["coverage"]:
        covered[c["status"]].append(c["facet"])
    assert "film" in covered.get("gap", [])
    assert "music" in covered.get("supported", [])
    assert report["claims"]  # successful facets were still synthesized

    # Conflicting statistic preserved with BOTH values (Task 5.6).
    assert len(report["contested"]) == 1
    values = {o["value"] for o in report["contested"][0]["observations"]}
    assert values == {"45%", "62%"}

    # The report surfaces the coverage gap explicitly.
    assert "GAP" in report["report_markdown"]
    assert "film" in report["report_markdown"]


def test_run_research_full_coverage_when_no_timeout():
    """Control: with no failure, every facet is supported and no gaps remain."""
    client = MockAnthropic(router=_research_router(timeout_facet="__none__"))
    report = coordinator.run_research(client, TOPIC)

    statuses = {c["facet"]: c["status"] for c in report["coverage"]}
    assert set(statuses) == {"visual arts", "music", "writing", "film"}
    assert all(s == "supported" for s in statuses.values())
    assert report["errors"] == []
