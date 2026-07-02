"""Starter scaffold: scoped tool distribution & tool_choice (Task Statement 2.3).

Implement the functions below so each agent role gets only the tools it needs,
so an over-provisioned tool set is flagged, and so ``tool_choice`` is chosen
correctly for the canonical cases.

``ALL_RESEARCH_TOOLS`` (the full 18-tool catalogue) is provided for you. Design
``ROLE_TOOLS`` (role -> the 4-5 tools that role needs) yourself, then use it in
``assign_tools``. See README.md for the full spec.

``run_forced_tool_call`` accepts an injected ``client`` so tests can pass a
MockAnthropic. This module is imported by the test suite (not run from a shell),
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


# Full (over-provisioned) catalogue for the research system: 18 tools. Handing
# all of these to one agent is the anti-pattern in Task 2.3. `fetch_url` is a
# generic tool intentionally replaced by the constrained `load_document`.
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

# TODO: map each role -> the 4-5 tool names it needs. Suggested roles:
#   coordinator, searcher, analyst, synthesis, writer.
#   Keep `verify_fact` OUT of the base synthesis set — it is added later via
#   add_scoped_cross_role_tool. Do NOT assign the deprecated `fetch_url`.
ROLE_TOOLS: dict[str, tuple[str, ...]] = {}

# TODO: pick the threshold above which a tool set is "too many" (4-5 is healthy).
MAX_RECOMMENDED_TOOLS = 7


def assign_tools(role: str, all_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the tools scoped to ``role`` from ``all_tools``.

    Restrict the subagent to its specialization. Raise ``ValueError`` for an
    unknown role.
    """
    # TODO: filter all_tools to the names in ROLE_TOOLS[role].
    raise NotImplementedError("Implement assign_tools (see README.md).")


def is_overprovisioned(tools: list[Any]) -> bool:
    """Return True when a tool set is large enough to degrade selection."""
    # TODO: flag sets larger than MAX_RECOMMENDED_TOOLS.
    raise NotImplementedError("Implement is_overprovisioned (see README.md).")


def add_scoped_cross_role_tool(agent: dict[str, Any], tool: Any) -> dict[str, Any]:
    """Add a scoped cross-role tool (e.g. ``verify_fact``) to ``agent``.

    ``agent`` is a config dict with ``"role"`` and ``"tools"``. Only add the tool
    if it is an allowed cross-role tool for that role; otherwise raise
    ``ValueError``. Return the updated agent (idempotent).
    """
    # TODO: guard against non-allow-listed cross-role tools, then append.
    raise NotImplementedError("Implement add_scoped_cross_role_tool (see README.md).")


def choose_tool_choice(scenario: Any) -> Any:
    """Map a scenario onto a ``tool_choice`` value.

    "auto" (may answer in text), "any" (must call some tool), or
    {"type": "tool", "name": ...} (must call a specific tool). See README.md.
    """
    # TODO: conversational -> "auto"; unknown_schema -> "any";
    #       force_extract_metadata_first -> {"type": "tool", "name": "extract_metadata"}.
    raise NotImplementedError("Implement choose_tool_choice (see README.md).")


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

    ``client`` is injected so tests can pass a MockAnthropic and assert on
    ``client.calls[-1]["tool_choice"]``.
    """
    # TODO: compute tool_choice via choose_tool_choice(scenario) and forward it
    #       to client.messages.create(...).
    raise NotImplementedError("Implement run_forced_tool_call (see README.md).")
