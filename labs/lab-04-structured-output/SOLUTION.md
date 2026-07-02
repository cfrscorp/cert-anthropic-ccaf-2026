# Lab 04 — Solution notes

## Approach

Model the desired output **as a tool's input schema**, force Claude to call that
tool, and read the structured data straight out of the `tool_use` block. The tool
is never "executed" — it exists purely so the API guarantees a schema-shaped
argument object. This is the recommended pattern for guaranteed structured output
(Task Statement 4.3).

Two modules:

- `schema.py` — the single source of truth for the tool (`name`, `description`,
  `input_schema`). Keeping the schema separate from the call logic makes it easy
  to review, test, and reuse.
- `extract.py` — `build_extraction_tool()` (copy of the tool),
  `extract(client, document, *, tool_choice=None)` (the API call + block read),
  and `pick_tool_choice(scenario)` (the `tool_choice` decision table).

## Key decisions & why

- **`input_schema` IS the output schema.** No JSON string parsing, no
  `json.loads` on a text block, no repair step for trailing commas. The API
  enforces types, required keys, and enums for us.

- **Default `tool_choice` forces the extraction tool.** For a pure extraction
  function you almost never want the model to reply conversationally. Forcing
  `{"type": "tool", "name": "extract_invoice"}` guarantees the response is a
  schema-compliant tool call. Callers can still override (e.g. pass `"any"` when
  routing across multiple schemas).

- **Nullable + required, not omitted.** `due_date` and `document_type_detail` are
  `"type": ["string", "null"]` **and** listed in `required`. This forces the
  model to address them on every document while giving it a truthful escape
  (`null`) when the information is absent — which is exactly what stops it from
  fabricating a plausible-but-wrong date to satisfy a non-null required field.

- **Optional means truly optional.** `purchase_order_number` and `line_items` are
  left out of `required`; the model may omit them entirely when they don't apply.

- **Enum + `"other"` + detail.** `document_type` is a closed enum ending in
  `"other"`, paired with the free-text `document_type_detail`. Categories stay
  controlled (good for downstream branching) yet extensible without a schema
  change.

- **`build_extraction_tool` returns a deep copy.** Tests and callers mutate the
  result; a copy keeps the shared module pristine (there's a test for this).

- **`extract` reads the named block first.** It prefers the block whose `name`
  matches the extraction tool, then falls back to any `tool_use` block (relevant
  under `"any"`), and returns `None` only when the model produced no tool call
  (possible under `"auto"`).

## Reference walkthrough

1. `build_extraction_tool()` → `copy.deepcopy(EXTRACTION_TOOL)`.
2. `extract(client, document)`:
   - build the tool; if `tool_choice is None`, set it to
     `{"type": "tool", "name": tool["name"]}`;
   - `client.messages.create(model=..., max_tokens=1024, tools=[tool],
     tool_choice=tool_choice, messages=[{"role": "user", "content": ...}])`;
   - collect `tool_use` blocks from `resp.content`; return the matching block's
     `dict(block.input)`, else the first tool_use block's input, else `None`.
3. `pick_tool_choice(scenario)` → dictionary lookup with a `ValueError` for
   unknown scenarios; dict results are copied so callers can't mutate the table.

The tests assert on `client.calls[0]` to confirm `tools` and `tool_choice` are
forwarded exactly — the mock records every `messages.create(**kwargs)`.

## Common mistakes

- **Parsing a text block instead of reading `tool_use`.** If you find yourself
  calling `json.loads(resp.text)`, you skipped the whole point. Read
  `block.input` from the `tool_use` block.
- **Making everything `required` and non-null.** The model will then invent
  values for missing data. Use nullable-required for "must consider, may be
  absent" and omit-from-required for "may not apply."
- **Using `"auto"` for a pure extraction.** `"auto"` lets the model answer with
  text and skip the tool — you can get `None`. Force the tool (or use `"any"`).
- **Forgetting the `"other"` detail field.** An `"other"` enum value with no
  place to record *what* it was throws away information.
- **Assuming the schema guarantees correctness.** It guarantees *shape*, not
  *meaning*. Line items may not sum to the total; a value may be in the wrong
  field. Add a semantic validation pass (Task Statement 4.4).
- **Mutating the shared tool dict.** Return a copy from `build_extraction_tool`.

## Checklist

- [ ] `build_extraction_tool()` returns `{name, description, input_schema}`.
- [ ] Schema has ≥1 nullable field (`type` list containing `"null"`).
- [ ] Schema has an enum field containing `"other"` + a paired detail field.
- [ ] Schema has ≥1 optional field (not in `required`).
- [ ] `extract` forwards `tools=[tool]` and the given/forced `tool_choice`.
- [ ] `extract` returns the `tool_use` block's `input` dict; passes `null`
      through unchanged; returns `None` when only text is returned.
- [ ] `pick_tool_choice` maps all three canonical scenarios and raises on others.
- [ ] `LAB_TARGET=solution uv run pytest lab-04-structured-output -q` is green.
