# Lab 05 — Tool Interface Design & Disambiguation

| | |
|---|---|
| **Domain** | 2 — Tool Design & MCP Integration |
| **Task statement** | 2.1 — Design effective tool interfaces with clear descriptions and boundaries |
| **Difficulty** | 4 / 10 |
| **Estimated time** | 1:15 |
| **Prerequisites** | L01 |

## Objective

Learn why **tool descriptions are the primary mechanism an LLM uses to select a
tool**, and practice the four techniques Task Statement 2.1 calls for:

1. Rewriting a minimal description to include an **input format**, an **example
   query**, **edge cases**, and a **"use this when ... not when ..." boundary**.
2. **Splitting** a generic tool into purpose-specific tools with defined I/O
   contracts.
3. **Renaming + rescoping** a tool to eliminate functional overlap.
4. **Detecting** when two descriptions are too similar to disambiguate — and
   reviewing system prompts for keyword-sensitive instructions that can override
   even good descriptions.

## Background

A support agent has four MCP tools with minimal descriptions (see
`tools_before.json`):

- `get_customer` — *"Retrieves details about a customer using an identifier."*
- `lookup_order` — *"Retrieves details about an order using an identifier."*
- `analyze_document` — *"Analyzes a document and returns useful information."*
- `analyze_content` — *"Analyzes content and returns an analysis of it."*

Production logs show the agent frequently calls `get_customer` when users ask
about orders ("check my order #12345"), because the two descriptions are
near-identical and both accept similar identifiers. This is exactly Sample
Question 2 in the exam guide: the **most effective first step is to expand each
tool's description** — not to add few-shot examples, not to build a routing
layer, and not to consolidate the tools. Descriptions are the highest-leverage,
lowest-effort fix because they address the root cause the model actually reads.

`analyze_document` is a second failure mode: one generic tool that tries to do
extraction, summarization, and claim-checking. The model can't tell which
behaviour a given call should produce. The fix is to **split** it into three
scoped tools. `analyze_content` overlaps with the document tools; the fix is to
**rename** it to something web-specific.

## Tasks

Work in `starter/`. Each function raises `NotImplementedError` until you
implement it; keep the same public API.

1. **`improve_description(tool: dict) -> dict`** — return a copy of the tool with
   a rewritten description that contains an input format, an example query,
   edge-case behaviour, and a `Use this when ... not when ...` boundary clause
   that references the sibling tool. The rewrites for `get_customer` and
   `lookup_order` must read as clearly distinct.

2. **`split_analyze_document() -> list[dict]`** — return exactly three tools named
   `extract_data_points`, `summarize_content`, and `verify_claim_against_source`,
   each with a distinct purpose and its own input/output contract.

3. **`rename_for_web(tool: dict) -> dict`** — rename `analyze_content` to
   `extract_web_results` and rescope its description to web content (search
   results / fetched pages).

4. **`describes_ambiguously(a: dict, b: dict) -> bool`** — return `True` when two
   descriptions are too similar to disambiguate (e.g. Jaccard similarity over
   content words above a threshold), `False` otherwise.

5. **Rewrite `starter/tools_after.json`** so all six target tools carry
   disambiguated descriptions (this is the artifact the optional LLM check and
   `test_tools_after_is_disambiguated` grade).

## Deliverables

- `starter/tool_design.py` with the four functions implemented.
- `starter/tools_after.json` rewritten with disambiguated descriptions for
  `get_customer`, `lookup_order`, the three split document tools, and
  `extract_web_results`.

## How to Verify

From the `labs/` directory:

```bash
uv run pytest lab-05-tool-interface-design
```

All deterministic tests should pass. The one semantic test is marked
`@pytest.mark.llm`; it is excluded from the default run and auto-skips unless you
export `ANTHROPIC_API_KEY`. To run it too:

```bash
ANTHROPIC_API_KEY=sk-... uv run pytest lab-05-tool-interface-design -m llm
```

## Stretch Goals

- **System-prompt keyword sensitivity.** Suppose the system prompt says *"When
  the user mentions their account, first pull up their customer record."* Explain
  how that keyword ("account") can override even a well-written `lookup_order`
  description when a user asks "what's on my account's latest order?" Draft a
  system-prompt wording that defers tool selection to the descriptions.
- **Structured error contract.** Extend `lookup_order` so a non-existent order
  returns a structured empty result (a successful query with no match) that the
  agent can distinguish from an access failure (Task Statement 2.2).
- **Tighten `describes_ambiguously`.** Make it also flag pairs where *both*
  descriptions are minimal (below a word-count floor) even when their wording
  differs, since minimal descriptions are inherently under-specified.
