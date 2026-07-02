"""Root pytest configuration shared by every lab.

- Puts labs/_shared on sys.path so tests can `import labkit`, `mock_anthropic`,
  and `grading` directly.
- Registers the `llm` marker (semantic tests requiring ANTHROPIC_API_KEY).
- Auto-skips `llm`-marked tests when no API key is present, so a plain
  `uv run pytest` is always deterministic and offline.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).parent / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "llm: test requires a live Claude call (needs ANTHROPIC_API_KEY); "
        "skipped by default via `-m 'not llm'` and auto-skipped without a key.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    skip_llm = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set; LLM-graded test skipped.")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)
