"""Reference solution for L05 — Tool Interface Design & Disambiguation.

Tool descriptions are the PRIMARY mechanism an LLM uses to select a tool
(exam guide, Task Statement 2.1 / Sample Question 2). Minimal, near-identical
descriptions cause misrouting between similar tools. The four functions below
demonstrate the four disambiguation techniques the task statement calls for:

1. improve_description       -> rewrite a minimal description to include input
                                format, an example query, edge cases, and a
                                "use this when ... not when ..." boundary.
2. split_analyze_document    -> split a generic tool into three purpose-specific
                                tools with defined I/O contracts.
3. rename_for_web            -> rename + rescope a tool to remove overlap.
4. describes_ambiguously     -> detect when two descriptions are too similar to
                                disambiguate reliably.

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

import re

__all__ = [
    "improve_description",
    "split_analyze_document",
    "rename_for_web",
    "describes_ambiguously",
]


# --------------------------------------------------------------------------- #
# 1. Rewrite minimal descriptions into disambiguating ones.
# --------------------------------------------------------------------------- #
# Each rewritten description contains the four elements Task Statement 2.1 asks
# for: an input format, an example query, edge-case behaviour, and an explicit
# boundary clause ("Use this when ... not when ...") that points at the sibling
# tool. The two customer/order descriptions are deliberately worded so that
# nothing about them overlaps enough to confuse the model.

_IMPROVED_DESCRIPTIONS: dict[str, str] = {
    "get_customer": (
        "Look up a customer's ACCOUNT PROFILE: name, email, phone, mailing "
        "address, loyalty tier, and account standing.\n\n"
        "Input format: {\"customer_id\": \"CUST-<digits>\"} (e.g. \"CUST-40912\") "
        "or {\"email\": \"person@example.com\"}. Accepts a customer ID or an "
        "email address; it does NOT accept an order number.\n\n"
        "Example query: \"What email do we have on file for account CUST-40912?\" "
        "or \"Is this customer's account in good standing?\"\n\n"
        "Edge cases: If more than one account matches an email, it returns "
        "multiple matches, ask the customer for their customer ID to "
        "disambiguate rather than guessing. It returns an empty result (not an "
        "error) when no account matches.\n\n"
        "Use this when the question is about WHO the customer is, their profile, "
        "contact information, or account standing, and not when the question is "
        "about a specific order's status, contents, or shipment (use "
        "lookup_order for that)."
    ),
    "lookup_order": (
        "Retrieve a single ORDER's status and contents: order status, line "
        "items, totals, shipment tracking number, and delivery dates.\n\n"
        "Input format: {\"order_id\": \"ORD-<digits>\"} (e.g. \"ORD-88213\"). "
        "Accepts an order number only; it does NOT accept a customer ID or "
        "email address.\n\n"
        "Example query: \"Where is my order #88213?\" or \"What items were in "
        "order ORD-88213 and has it shipped yet?\"\n\n"
        "Edge cases: It returns an empty result (not an error) when the order "
        "number does not exist. A cancelled order still returns its record with "
        "status \"cancelled\". It does not return other orders belonging to the "
        "same customer.\n\n"
        "Use this when the question is about a SPECIFIC order, its status, "
        "items, or shipment, and not when the question is about the customer's "
        "profile or listing all of their orders (use get_customer for "
        "account-level questions)."
    ),
}


def improve_description(tool: dict) -> dict:
    """Return a copy of ``tool`` with a disambiguating description.

    The rewritten description includes an input format, an example query,
    edge-case behaviour, and a "Use this when ... not when ..." boundary clause
    that references the sibling tool.
    """
    improved = dict(tool)
    name = tool.get("name", "")
    if name in _IMPROVED_DESCRIPTIONS:
        improved["description"] = _IMPROVED_DESCRIPTIONS[name]
        return improved

    # Generic fallback for any other minimal tool: keep the original intent but
    # graft on the four required elements so the shape is always correct.
    original = (tool.get("description") or "").strip().rstrip(".")
    improved["description"] = (
        f"{original}.\n\n"
        "Input format: state the exact accepted input, e.g. "
        "{\"id\": \"<identifier>\"}.\n\n"
        "Example query: give one concrete example request this tool answers.\n\n"
        "Edge cases: describe empty-result, multiple-match, and missing-data "
        "behaviour.\n\n"
        "Use this when this tool is the best fit for the request, and not when "
        "a more specific sibling tool covers it."
    )
    return improved


# --------------------------------------------------------------------------- #
# 2. Split the generic analyze_document into three purpose-specific tools.
# --------------------------------------------------------------------------- #
def split_analyze_document() -> list[dict]:
    """Split the generic ``analyze_document`` into three scoped tools.

    Returns exactly three tools, each with a distinct purpose and a defined
    input/output contract:

    - extract_data_points        -> pull named field values as JSON
    - summarize_content          -> produce a prose summary
    - verify_claim_against_source -> confirm/refute one claim against the source
    """
    return [
        {
            "name": "extract_data_points",
            "description": (
                "Extract specific STRUCTURED FIELD VALUES from a document "
                "(dates, amounts, names, IDs, line items) and return them as "
                "JSON.\n\n"
                "Input format: {\"document\": \"<full document text>\", "
                "\"fields\": [\"invoice_number\", \"total_amount\", "
                "\"due_date\"]}. `fields` names the exact data points to pull.\n\n"
                "Example query: \"Pull the invoice number, total, and due date "
                "from this invoice.\"\n\n"
                "Edge cases: When a requested field is absent from the document, "
                "return null for that field rather than fabricating a value.\n\n"
                "Use this when you need discrete field values out of a document, "
                "and not when you need a prose summary (use summarize_content) "
                "or a yes/no check of a claim (use verify_claim_against_source)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "document": {"type": "string"},
                    "fields": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["document", "fields"],
            },
        },
        {
            "name": "summarize_content",
            "description": (
                "Produce a concise NATURAL-LANGUAGE SUMMARY of a document's "
                "main points.\n\n"
                "Input format: {\"document\": \"<full document text>\", "
                "\"max_words\": 150}.\n\n"
                "Example query: \"Give me a two-paragraph summary of this "
                "contract.\"\n\n"
                "Edge cases: For very long documents, summarize section by "
                "section; do not silently drop the middle.\n\n"
                "Use this when you need a human-readable overview of what a "
                "document says, and not when you need specific field values "
                "(use extract_data_points) or to confirm one statement (use "
                "verify_claim_against_source)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "document": {"type": "string"},
                    "max_words": {"type": "integer"},
                },
                "required": ["document"],
            },
        },
        {
            "name": "verify_claim_against_source",
            "description": (
                "Check whether a SPECIFIC CLAIM is supported, contradicted, or "
                "unaddressed by a source document, returning a verdict plus the "
                "supporting excerpt.\n\n"
                "Input format: {\"document\": \"<full document text>\", "
                "\"claim\": \"The contract auto-renews annually.\"}.\n\n"
                "Example query: \"Does this contract actually say it "
                "auto-renews?\"\n\n"
                "Edge cases: If the document neither supports nor contradicts "
                "the claim, return \"unsupported\" rather than guessing.\n\n"
                "Use this when you need to confirm or refute one statement "
                "against a source, and not when you need to extract fields (use "
                "extract_data_points) or summarize the whole document (use "
                "summarize_content)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "document": {"type": "string"},
                    "claim": {"type": "string"},
                },
                "required": ["document", "claim"],
            },
        },
    ]


# --------------------------------------------------------------------------- #
# 3. Rename + rescope analyze_content -> extract_web_results.
# --------------------------------------------------------------------------- #
def rename_for_web(tool: dict) -> dict:
    """Rename ``analyze_content`` to ``extract_web_results`` with a web-specific
    description, eliminating its overlap with the document tools."""
    renamed = dict(tool)
    renamed["name"] = "extract_web_results"
    renamed["description"] = (
        "Extract the relevant RESULTS FROM WEB CONTENT (a web search response or "
        "a fetched web page): titles, URLs, snippets, and publication dates, "
        "returned as structured entries.\n\n"
        "Input format: {\"query\": \"<original search query>\", "
        "\"page_or_results\": \"<raw search results or fetched page content>\"}."
        "\n\n"
        "Example query: \"From these search results, pull the top 5 article "
        "titles, links, and dates.\"\n\n"
        "Edge cases: Skip ads and navigation chrome; return an empty list when "
        "the page has no substantive results.\n\n"
        "Use this when the source is web content (search results or a fetched "
        "page), and not when the source is an internal document (use "
        "extract_data_points or summarize_content instead)."
    )
    renamed["input_schema"] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "page_or_results": {"type": "string"},
        },
        "required": ["page_or_results"],
    }
    return renamed


# --------------------------------------------------------------------------- #
# 4. Detect near-identical (ambiguous) descriptions.
# --------------------------------------------------------------------------- #
# Two tools are "ambiguous" when their descriptions share so many content words
# (and offer so little distinguishing detail) that the model cannot reliably
# tell them apart. We measure this with Jaccard similarity over content tokens.

_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "from", "this", "that", "using", "about",
        "their", "its", "them", "into", "onto", "returns", "return", "when",
        "not", "use", "used", "which", "what", "who", "you", "your", "are",
        "was", "were", "has", "have", "had", "will", "would", "can", "may",
        "one", "two", "three", "information", "detail", "details",
    }
)

_AMBIGUITY_THRESHOLD = 0.5


def _content_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def describes_ambiguously(a: dict, b: dict, threshold: float = _AMBIGUITY_THRESHOLD) -> bool:
    """Return True when two tools' descriptions are too similar to disambiguate.

    Uses Jaccard similarity over content tokens (ignoring common stop words).
    A pair of minimal, near-identical descriptions scores high (ambiguous);
    a pair of rich, purpose-specific descriptions scores low (unambiguous).
    """
    ta = _content_tokens(a.get("description", ""))
    tb = _content_tokens(b.get("description", ""))
    if not ta or not tb:
        return False
    similarity = len(ta & tb) / len(ta | tb)
    return similarity >= threshold
