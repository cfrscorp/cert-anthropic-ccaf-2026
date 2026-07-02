# Shared lab harness — contract for lab authors

Everything in `labs/_shared/` is importable from any lab's tests because the root
`labs/conftest.py` puts this directory on `sys.path`. **Do not edit these files
inside a lab** — extend within your own lab folder if you need more.

## What every lab folder looks like

```
lab-NN-slug/
  README.md         # learner-facing instructions (template below)
  SOLUTION.md       # reference solution, hints, pitfalls
  starter/          # scaffold with TODOs — the learner edits this
  solution/         # complete reference implementation (same public API as starter/)
  tests/test_labNN.py
  <config files as needed>   # .mcp.json, .claude/rules/*.md, SKILL.md, *.yml, sample docs
```

`starter/` and `solution/` **must expose the same module names and public
functions/classes**, so the same test file passes against `solution/` and fails
against an unfinished `starter/`.

## Importing the module under test

```python
# tests/test_labNN.py
from labkit import lab_module

mod = lab_module(__file__, "agent_loop")   # loads starter/agent_loop.py by default
```

- `uv run pytest` (default) → tests import from `starter/` (the learner's work).
- `LAB_TARGET=solution uv run pytest` → tests import from `solution/` (used by the
  program's validation pass; every lab's solution MUST be green this way).

## Mocking Claude (deterministic, offline)

```python
from mock_anthropic import MockAnthropic, text_response, tool_use_response

# Scripted, consumed in order:
client = MockAnthropic(responses=[
    tool_use_response("lookup_order", {"order_id": "A1"}),
    text_response("Your order shipped Tuesday."),
])

# Or dynamic, based on the incoming request:
def router(req, calls):
    last = req["messages"][-1]
    ...
    return text_response("...")
client = MockAnthropic(router=router)

client.calls          # every messages.create(**kwargs), in order — assert on tool_choice, tools, etc.
```

Response objects mimic the SDK: `resp.stop_reason`, `resp.content` (list of
`TextBlock`/`ToolUseBlock`), `resp.text`, `resp.tool_use_blocks()`, `resp.usage`.

Pass the client into the learner's code (dependency injection). Learner functions
should accept a `client` parameter rather than constructing `anthropic.Anthropic()`
internally, so tests can inject the mock.

### Batch API

```python
client = MockAnthropic(batch_handler=lambda cid, params: ("succeeded", text_response("ok")))
batch = client.messages.batches.create(requests=[{"custom_id": "doc-1", "params": {...}}])
results = client.messages.batches.results(batch.id)   # list with .custom_id and .result
```

## Semantic grading (only when unavoidable)

```python
import pytest
from grading import grade, require_llm

@pytest.mark.llm
def test_is_semantic():
    require_llm()                      # skips if no ANTHROPIC_API_KEY
    v = grade(rubric="...", submission=open("solution/out.txt").read())
    assert v["pass"], v["reason"]
```

Mark such tests `@pytest.mark.llm`. The default `addopts` excludes them, and they
auto-skip without a key. Prefer deterministic assertions; reach for `grade` only
for meaning a structural check cannot verify.

## Runnable scripts

Any script a learner runs from a shell must follow the user's global conventions:
PEP 723 inline metadata (`uv run`-able), `argparse` with `-h/--help` + an Examples
epilog (`RawDescriptionHelpFormatter`), a module-level `__version__`, and a
`--version` action. Config-only labs (CLAUDE.md, rules, `.mcp.json`) are exempt.
