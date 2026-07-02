"""Starter scaffold for L05 — Tool Interface Design & Disambiguation.

Implement the four functions below, then rewrite ``tools_after.json`` in this
directory so its tool descriptions actually disambiguate. Run the tests with:

    uv run pytest lab-05-tool-interface-design      # from labs/

Tool descriptions are the PRIMARY mechanism an LLM uses to select a tool
(exam guide, Task Statement 2.1 / Sample Question 2). Your job is to turn
minimal, near-identical descriptions into ones that clearly differentiate each
tool's purpose, inputs, edge cases, and boundaries.

This module is imported by the test suite; it is not a shell script, so the
PEP 723 / argparse conventions do not apply.
"""

from __future__ import annotations

__all__ = [
    "improve_description",
    "split_analyze_document",
    "rename_for_web",
    "describes_ambiguously",
]


def improve_description(tool: dict) -> dict:
    """Return a copy of ``tool`` with a disambiguating description.

    The rewritten description MUST include:
      - an input format (what identifiers/shape the tool accepts),
      - an example query,
      - edge-case behaviour,
      - a "Use this when ... not when ..." boundary clause that references the
        sibling tool it is most often confused with.

    TODO: implement. Keep the description for get_customer and lookup_order
    clearly distinct from one another.
    """
    raise NotImplementedError("Implement improve_description")


def split_analyze_document() -> list[dict]:
    """Split the generic ``analyze_document`` into three purpose-specific tools.

    Return exactly three tools named:
      - extract_data_points          (pull named field values as JSON)
      - summarize_content            (produce a prose summary)
      - verify_claim_against_source  (confirm/refute one claim against a source)

    Each must have a distinct description and its own input/output contract.

    TODO: implement.
    """
    raise NotImplementedError("Implement split_analyze_document")


def rename_for_web(tool: dict) -> dict:
    """Rename ``analyze_content`` to ``extract_web_results`` and rescope its
    description to be web-specific (search results / fetched pages), removing
    its overlap with the document tools.

    TODO: implement.
    """
    raise NotImplementedError("Implement rename_for_web")


def describes_ambiguously(a: dict, b: dict) -> bool:
    """Return True when two tools' descriptions are too similar to disambiguate.

    Hint: compare the sets of meaningful content words in each description
    (e.g. Jaccard similarity, ignoring common stop words) and flag pairs above
    a threshold. It must return True for the minimal before-pair and False for
    the rewritten after-pair.

    TODO: implement.
    """
    raise NotImplementedError("Implement describes_ambiguously")
