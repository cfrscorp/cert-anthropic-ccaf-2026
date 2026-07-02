"""Reference solution for L09 — scoped tool distribution & tool_choice.

Exam Task Statement 2.3 ("Distribute tools appropriately across agents and
configure tool choice"). Two linked ideas:

1. Scoped tool access. Giving one agent 18 tools instead of the 4-5 it needs
   degrades tool selection: more near-neighbours to choose between means more
   misrouting. Agents also *misuse* tools outside their specialization (a
   synthesis agent trying to run web searches). Each subagent should therefore
   get only the tools its role needs, plus a small number of scoped cross-role
   tools for high-frequency needs (e.g. a `verify_fact` tool for synthesis).

2. tool_choice. Three settings control whether/which tool the model calls:
       "auto"                      -> may call a tool OR answer in text
       "any"                       -> MUST call some tool (it picks which)
       {"type": "tool", "name": …} -> MUST call that specific tool (forced)

This models Scenario 3 (multi-agent research system). ``ALL_RESEARCH_TOOLS`` is
the full, over-provisioned catalogue; ``ROLE_TOOLS`` is the scoped assignment.

This module is imported by the test suite. ``run_forced_tool_call`` accepts an
injected ``client`` so tests can pass a MockAnthropic; it is not a shell script,
so the PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ALL_RESEARCH_TOOLS",
    "ROLE_TOOLS",
    "MAX_RECOMMENDED_TOOLS",
    "assign_tools",
    "is_overprovisioned",
    "add_scoped_cross_role_tool",
    "choose_tool_choice",
    "run_forced_tool_call",
]


def _tool(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": {}},
    }


# --------------------------------------------------------------------------- #
# The full (over-provisioned) tool catalogue for the research system: 18 tools.
# Handing all of these to any single agent is the anti-pattern in Task 2.3.
# Note: `fetch_url` is a generic tool intentionally REPLACED by the constrained
# `load_document`; it is assigned to no role below.
# --------------------------------------------------------------------------- #
ALL_RESEARCH_TOOLS: list[dict[str, Any]] = [
    _tool("web_search", "Run a web search query and return ranked result entries."),
    _tool("fetch_url", "Fetch any URL and return its raw contents (generic; deprecated)."),
    _tool("load_document", "Fetch a validated document URL (allow-listed hosts) as text."),
    _tool("extract_web_results", "Pull titles, URLs, snippets, dates from web results."),
    _tool("extract_data_points", "Extract named field values from a document as JSON."),
    _tool("summarize_content", "Produce a prose summary of a document."),
    _tool("verify_claim_against_source", "Confirm/refute a claim against a source doc."),
    _tool("verify_fact", "Look up a single simple fact (date, name, statistic)."),
    _tool("synthesize_findings", "Merge findings from subagents into a coherent draft."),
    _tool("detect_coverage_gaps", "Identify topic areas missing from current findings."),
    _tool("generate_report", "Render a final cited report from synthesized findings."),
    _tool("format_citations", "Format claim-source mappings into citations."),
    _tool("delegate_task", "Spawn a subagent with a scoped task (the Task tool)."),
    _tool("aggregate_results", "Collect and merge subagent outputs for the coordinator."),
    _tool("evaluate_coverage", "Judge whether synthesis coverage is sufficient."),
    _tool("rerank_sources", "Reorder candidate sources by relevance to the query."),
    _tool("translate_text", "Translate text between languages."),
    _tool("export_pdf", "Export a finished report to PDF."),
]

# --------------------------------------------------------------------------- #
# Scoped assignments: each role gets ONLY the 3-5 tools it needs. `verify_fact`
# is a scoped cross-role tool added to synthesis separately (see
# add_scoped_cross_role_tool); it is NOT part of the base synthesis set.
# --------------------------------------------------------------------------- #
ROLE_TOOLS: dict[str, tuple[str, ...]] = {
    "coordinator": ("delegate_task", "aggregate_results", "evaluate_coverage", "detect_coverage_gaps"),
    "searcher": ("web_search", "load_document", "extract_web_results", "rerank_sources"),
    "analyst": ("load_document", "extract_data_points", "summarize_content", "verify_claim_against_source"),
    "synthesis": ("synthesize_findings", "detect_coverage_gaps", "format_citations"),
    "writer": ("generate_report", "format_citations", "export_pdf", "translate_text"),
}

# Cross-role tools an agent may hold beyond its base set, keyed by role. Kept
# deliberately tiny: only high-frequency needs, everything else routes through
# the coordinator (Sample Question 9).
_ALLOWED_CROSS_ROLE: dict[str, frozenset[str]] = {
    "synthesis": frozenset({"verify_fact"}),
}

# 4-5 tools is the healthy range; anything materially larger degrades selection.
MAX_RECOMMENDED_TOOLS = 7


def _tool_name(tool: Any) -> str:
    """Accept a tool dict or a bare name string; return the name."""
    if isinstance(tool, str):
        return tool
    if isinstance(tool, dict):
        return tool.get("name", "")
    raise TypeError(f"tool must be a dict or str, got {type(tool).__name__}")


def assign_tools(role: str, all_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the tools scoped to ``role`` from ``all_tools``.

    This restricts a subagent to its specialization: a searcher gets search
    tools, a synthesis agent gets synthesis tools, and neither can reach for the
    other's. Preserves the order of ``all_tools`` and only returns tools that are
    actually present in the catalogue. Raises ``ValueError`` for an unknown role.
    """
    if role not in ROLE_TOOLS:
        raise ValueError(f"unknown role {role!r}; expected one of {tuple(ROLE_TOOLS)}")
    allowed = set(ROLE_TOOLS[role])
    return [t for t in all_tools if _tool_name(t) in allowed]


def is_overprovisioned(tools: list[Any]) -> bool:
    """Return True when a tool set is large enough to degrade selection.

    A healthy per-agent set is ~4-5 tools; a set beyond
    :data:`MAX_RECOMMENDED_TOOLS` (e.g. the full 18-tool catalogue) is flagged.
    Accepts a list of tool dicts or bare names.
    """
    return len(tools) > MAX_RECOMMENDED_TOOLS


def add_scoped_cross_role_tool(agent: dict[str, Any], tool: Any) -> dict[str, Any]:
    """Add a scoped cross-role tool (e.g. ``verify_fact``) to ``agent``.

    ``agent`` is a config dict with ``"role"`` and ``"tools"`` (a list). The tool
    is only added if it is on the allow-list of cross-role tools for that role;
    otherwise ``ValueError`` is raised — this guard is what stops an agent from
    quietly accumulating out-of-specialization tools and becoming
    over-provisioned. Returns a shallow copy of ``agent`` with the tool appended
    (idempotent: adding an already-present tool is a no-op).
    """
    role = agent.get("role")
    name = _tool_name(tool)
    permitted = _ALLOWED_CROSS_ROLE.get(role, frozenset())
    if name not in permitted:
        raise ValueError(
            f"{name!r} is not an allowed cross-role tool for role {role!r}; "
            f"route complex needs through the coordinator instead of widening "
            f"the agent's tool set. Allowed: {tuple(permitted)}"
        )
    updated = dict(agent)
    tools = list(updated.get("tools", []))
    if all(_tool_name(t) != name for t in tools):
        tools.append(tool)
    updated["tools"] = tools
    return updated


# --------------------------------------------------------------------------- #
# tool_choice selection for the canonical Task 2.3 / 4.3 cases.
# --------------------------------------------------------------------------- #
_AUTO_SCENARIOS = {"conversational", "auto", "may_use_tool", "chit_chat"}
_ANY_SCENARIOS = {
    "any", "unknown_schema", "guarantee_tool_use", "must_call_a_tool",
    "structured_output_required", "no_text_response",
}
# Scenario -> tool name to force. Extend as needed.
_FORCE_SCENARIOS = {
    "force_extract_metadata_first": "extract_metadata",
    "extract_metadata_first": "extract_metadata",
    "metadata_before_enrichment": "extract_metadata",
}


def choose_tool_choice(scenario: Any) -> Any:
    """Map a scenario onto a ``tool_choice`` value.

    Returns:
        - ``"auto"``  when the model may answer in text (conversational turns).
        - ``"any"``   when the model MUST call some tool but may pick which (e.g.
          the document type is unknown and any of several extraction schemas
          would do — guarantee structured output rather than a text reply).
        - ``{"type": "tool", "name": <name>}`` when a SPECIFIC tool must run
          first (e.g. force ``extract_metadata`` before enrichment steps).

    ``scenario`` may be a known string key, or a dict like
    ``{"force": "tool_name"}`` to force an arbitrary named tool.
    """
    if isinstance(scenario, dict):
        # Explicit forced form: {"force": "tool_name"}.
        forced = scenario.get("force") or scenario.get("tool")
        if forced:
            return {"type": "tool", "name": forced}
        raise ValueError(f"unrecognised tool_choice scenario dict: {scenario!r}")

    key = str(scenario).strip().lower()
    if key in _AUTO_SCENARIOS:
        return "auto"
    if key in _ANY_SCENARIOS:
        return "any"
    if key in _FORCE_SCENARIOS:
        return {"type": "tool", "name": _FORCE_SCENARIOS[key]}
    raise ValueError(
        f"unknown tool_choice scenario {scenario!r}; expected conversational -> "
        f"'auto', unknown_schema -> 'any', or force_extract_metadata_first -> forced"
    )


def run_forced_tool_call(
    client: Any,
    scenario: Any,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    model: str = "claude-mock",
    max_tokens: int = 1024,
) -> Any:
    """Call the model with the ``tool_choice`` selected by ``scenario``.

    Demonstrates that the chosen ``tool_choice`` is actually forwarded to the
    API. ``client`` is injected (dependency injection) so tests can pass a
    ``MockAnthropic`` and assert on ``client.calls[-1]["tool_choice"]``.
    """
    tool_choice = choose_tool_choice(scenario)
    return client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )
