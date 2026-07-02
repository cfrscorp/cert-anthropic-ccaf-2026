# Lab 05 — Reference Solution

## Approach

The lab exercises the four skills under Task Statement 2.1, each as one function
in `solution/tool_design.py`, plus the concrete artifact `solution/tools_after.json`:

1. **Rewrite descriptions** (`improve_description`) so the model has the context
   it needs: input format, an example query, edge cases, and an explicit
   boundary that names the sibling tool.
2. **Split** the generic `analyze_document` (`split_analyze_document`) into three
   tools with non-overlapping purposes and I/O contracts.
3. **Rename + rescope** `analyze_content` (`rename_for_web`) to
   `extract_web_results` so it stops competing with the document tools.
4. **Detect ambiguity** (`describes_ambiguously`) so the improvement is
   measurable: the before-pair reads as ambiguous, the after-pair does not.

## Key decisions & why

**Descriptions are the first-line fix, before few-shot / routing / consolidation.**
This is the crux of Sample Question 2. When an agent misroutes between two
similar tools with minimal descriptions, the *root cause* is that the model
lacks the information it selects on. Options that add few-shot examples (token
overhead, doesn't fix the root cause), a routing layer (over-engineered, bypasses
the model's own language understanding), or consolidate the two tools into one
(a valid architecture change, but more effort than a "first step" warrants) all
rank below simply expanding the descriptions. So `improve_description` is the
centerpiece, and the LLM check grades the resulting `tools_after.json`.

**Every rewritten description carries four elements.** Input format tells the
model which identifiers each tool accepts (`CUST-...` vs `ORD-...`) — this alone
resolves most of the get_customer/lookup_order confusion. The example query
anchors the intent. Edge cases (empty result vs error, multiple matches)
pre-empt mis-selection on boundary inputs. The `Use this when ... not when ...`
clause explicitly cross-references the sibling tool, which is what actually
separates two otherwise-adjacent tools.

**Splitting encodes intent in the tool boundary, not the prompt.** A generic
`analyze_document` forces the model to infer, per call, whether it should
extract, summarize, or verify. Three named tools make that a selection decision
driven by the description — far more reliable — and each gets its own
input/output contract (`fields` list, `max_words`, `claim`).

**Ambiguity as a measurable property.** `describes_ambiguously` uses Jaccard
similarity over content tokens (stop words removed). The before-pair
("Retrieves details about a customer/order using an identifier.") scores 0.6 and
is flagged; the rewritten pair shares only incidental words against a large
vocabulary and scores well under the 0.5 threshold. This makes "did the rewrite
help?" a test assertion rather than a judgment call.

## Reference walkthrough

- `improve_description` dispatches on `tool["name"]` to canonical rewrites for
  `get_customer` / `lookup_order`, with a generic fallback that still grafts on
  the four required elements for any other tool.
- `split_analyze_document` returns the three tools verbatim with distinct
  descriptions and schemas.
- `rename_for_web` sets `name = "extract_web_results"`, swaps in a web-specific
  description, and gives it a web-shaped schema (`query`, `page_or_results`).
- `describes_ambiguously` tokenizes, drops stop words and short tokens, and
  compares Jaccard similarity to a 0.5 threshold.
- `solution/tools_after.json` is the assembled target: the two rewritten support
  tools, the three split document tools, and the renamed web tool. Its
  get_customer/lookup_order descriptions match the strings in `tool_design.py`.

## Common mistakes

- **Adding few-shot examples instead of fixing descriptions.** Correct as a
  *later* refinement, but not the first step — and it doesn't fix the root cause.
- **Boundary clause that doesn't name the other tool.** "Use this for orders" is
  weaker than "...and not when the question is about the customer's profile (use
  get_customer)." The cross-reference is what disambiguates.
- **Leaving the split tools' descriptions near-identical** (all three starting
  "Analyzes the document..."). The names change but the model still can't choose;
  the descriptions must describe *different behaviour*.
- **Renaming without rescoping.** Changing only the `name` to
  `extract_web_results` while keeping "Analyzes content and returns an analysis"
  leaves the overlap in place. The description must become web-specific.
- **Ignoring system-prompt keyword sensitivity.** A description can be perfect
  and still be overridden by a system prompt that hard-wires a keyword
  ("account" -> get_customer). Review the prompt too (stretch goal).

## Checklist

- [ ] `improve_description` output contains input format, example query, edge
      cases, and a "Use this when ... not when ..." boundary.
- [ ] Improved `get_customer` and `lookup_order` descriptions are distinct and no
      longer flagged by `describes_ambiguously`.
- [ ] `split_analyze_document` returns exactly `extract_data_points`,
      `summarize_content`, `verify_claim_against_source`, with distinct descriptions.
- [ ] `rename_for_web` returns `extract_web_results` with a web-specific description.
- [ ] `describes_ambiguously` is `True` for the before-pair, `False` for the after-pair.
- [ ] `tools_after.json` contains all six disambiguated tools.
- [ ] `LAB_TARGET=solution uv run pytest lab-05-tool-interface-design` is green;
      the default (starter) run fails until the functions are implemented.
