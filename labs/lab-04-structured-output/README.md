# Lab 04 — Structured Output via `tool_use`

| | |
|---|---|
| **Difficulty** | 3 / 10 |
| **Estimated time** | 1:30 |
| **Prerequisites** | L01 |
| **Exam mapping** | Task Statement 4.3 (also 2.3 for `tool_choice`) |

## Objective

Learn the most reliable way to get **guaranteed schema-compliant structured
output** from Claude: define a *tool* whose `input_schema` is your output schema,
ask Claude to call it, and read the structured data out of the returned
`tool_use` block. Along the way you will practice `tool_choice` selection and the
schema-design patterns that keep extractions honest.

By the end you can:

- Define an extraction tool whose `input_schema` **is** the output schema, and
  pull the result from the `tool_use` block.
- Choose between `tool_choice: "auto"`, `"any"`, and forced
  `{"type": "tool", "name": "..."}` — and explain when each is correct.
- Design schemas with **required vs optional** fields, **nullable** fields (so
  the model returns `null` instead of fabricating), and an **enum with `"other"`
  + detail** for extensible categories.
- Explain why a strict schema removes JSON *syntax* errors but **not** *semantic*
  errors.

## Background

Prompting Claude to "reply with JSON" works until it doesn't: a stray comment,
a trailing comma, or a hallucinated field breaks your parser. Tool use fixes the
*structural* half of this problem. When you register a tool, its `input_schema`
is a JSON Schema; when Claude calls the tool, the API guarantees the tool
`input` conforms to that schema. So you model your desired output **as a tool's
input** and never hand-parse a JSON string again.

Three `tool_choice` modes control *whether/which* tool gets called:

| `tool_choice` | Meaning | Use when |
|---|---|---|
| `"auto"` | Model may call a tool **or** reply with text | The turn might legitimately be conversational |
| `"any"` | Model **must** call **some** tool (its choice) | You have several extraction schemas and don't yet know the document type |
| `{"type": "tool", "name": "x"}` | Model **must** call tool `x` | You need a specific extraction to run (e.g. `extract_metadata` before enrichment) |

Schema design still matters because syntax-safety is not correctness:

- **Required vs optional** — list only truly-mandatory fields in `required`;
  leave genuinely-optional ones out so the model may omit them.
- **Nullable fields** — make a field `"type": ["string", "null"]` and keep it
  `required`. The model must address it every time but can answer `null` when
  the document doesn't contain the info — instead of inventing a value to
  satisfy a non-null required field.
- **Enum + `"other"` + detail** — a closed enum with an `"other"` value paired
  with a free-text detail field keeps categories controlled yet extensible.

And the big caveat: a strict schema eliminates **syntax** errors (malformed JSON,
missing keys, wrong types) but **not semantic** errors. Nothing in a schema
guarantees that `line_items` sum to `total_amount`, or that a value landed in the
right field. Those are validation concerns (Task Statement 4.4), not schema
concerns.

## Tasks

You will complete two files in `starter/`:

### 1. `starter/schema.py` — finish the extraction tool's schema

Complete `INPUT_SCHEMA` (and the small constants above it) so it demonstrates all
four techniques:

- a required, non-null field (already present) **and** at least one **optional**
  field (not listed in `required`);
- at least one **nullable** field (`"type": ["string", "null"]`) that IS in
  `required`;
- a `document_type` **enum** that includes `"other"`;
- a paired nullable **detail** field for the `"other"` case;
- a `description` that tells the model to return `null` rather than fabricate.

### 2. `starter/extract.py` — implement the public API

- `build_extraction_tool() -> dict` — return a **copy** of `EXTRACTION_TOOL`.
- `extract(client, document, *, tool_choice=None) -> dict | None` — call
  `client.messages.create(tools=[tool], tool_choice=..., messages=[...])`; when
  `tool_choice` is `None`, **default to forcing the extraction tool**; return the
  `tool_use` block's `input` dict (or `None` if the model returned only text).
- `pick_tool_choice(scenario: str) -> object` — map the canonical scenarios:
  - `"unknown_document_type"` → `"any"`
  - `"must_extract_metadata_first"` → `{"type": "tool", "name": "extract_metadata"}`
  - `"conversational_allowed"` → `"auto"`
  - anything else → raise `ValueError`.

Inject the client (never construct `anthropic.Anthropic()` inside these
functions) so the tests can run offline against `MockAnthropic`.

## Deliverables

- Completed `starter/schema.py` and `starter/extract.py` with the same public API
  as `solution/`.
- All deterministic tests in `tests/test_lab04.py` passing.

## How to verify

From the `labs/` directory:

```bash
uv run pytest lab-04-structured-output
```

To compare against the reference solution:

```bash
LAB_TARGET=solution uv run pytest lab-04-structured-output -q
```

The optional semantic check is skipped unless you opt in with a key:

```bash
ANTHROPIC_API_KEY=... uv run pytest lab-04-structured-output -m llm
```

## Stretch goals

1. **Semantic validation.** After `extract`, add a `validate(result)` that flags
   when `sum(item["amount"] for item in line_items)` ≠ `total_amount` — the
   semantic error a schema can't catch. (Preview of Task Statement 4.4.)
2. **Multi-schema routing.** Register two tools (`extract_invoice`,
   `extract_receipt`), call with `tool_choice="any"`, and branch on which tool
   the model chose.
3. **`unclear` enum value.** Add an `"unclear"` enum member for ambiguous
   documents and adjust the description so the model uses it instead of guessing.
4. **Format normalization.** Add prompt rules (e.g. dates → ISO 8601, currency →
   ISO 4217) so inconsistent source formats normalize despite a strict schema.
