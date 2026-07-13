"""Deterministic, offline validation of the CCAF study content.

Every data file is validated against its JSON Schema, then cross-checked for
integrity (valid answer keys, complete distractor rationales, real task
statements, resolvable lab links) and coverage. Mirrors the labs' philosophy:
the content cannot silently break the web app.

Coverage is gated by PILOT_DOMAINS: during the pilot only Domain 1 must meet the
per-task-statement question target; widen PILOT_DOMAINS to {1,2,3,4,5} once all
domains are authored.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

STUDY_ROOT = Path(__file__).resolve().parent.parent
DATA = STUDY_ROOT / "data"
SCHEMA = DATA / "schema"
LABS_ROOT = STUDY_ROOT.parent / "labs"

PILOT_DOMAINS = {1, 2, 3, 4, 5}  # all domains authored


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


META = _load(DATA / "meta.json")
QUESTIONS = _load(DATA / "questions.json")
FLASHCARDS = _load(DATA / "flashcards.json")
CONCEPTS = _load(DATA / "concepts.json")
LABS = _load(DATA / "labs.json")
TASK_IDS = {ts["id"] for ts in META["task_statements"]}
TASK_DOMAIN = {ts["id"]: ts["domain"] for ts in META["task_statements"]}


# --------------------------------------------------------------------------- #
# Schema validation                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "data_file, schema_file",
    [
        ("meta.json", "meta.schema.json"),
        ("questions.json", "questions.schema.json"),
        ("flashcards.json", "flashcards.schema.json"),
        ("concepts.json", "concepts.schema.json"),
        ("labs.json", "labs.schema.json"),
    ],
)
def test_data_matches_schema(data_file, schema_file):
    data = _load(DATA / data_file)
    schema = _load(SCHEMA / schema_file)
    jsonschema.validate(instance=data, schema=schema)


# --------------------------------------------------------------------------- #
# Meta integrity                                                               #
# --------------------------------------------------------------------------- #
def test_domain_weights_sum_to_100():
    assert sum(d["weight"] for d in META["domains"]) == 100


def test_task_statement_domains_are_consistent():
    for ts in META["task_statements"]:
        assert ts["id"].startswith(str(ts["domain"])), ts


def test_meta_lab_links_resolve():
    for ts in META["task_statements"]:
        for lab in ts["labs"]:
            assert (LABS_ROOT / lab).is_dir(), f"{ts['id']} → missing lab {lab}"


# --------------------------------------------------------------------------- #
# Question integrity                                                           #
# --------------------------------------------------------------------------- #
def test_question_ids_unique():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids)), "duplicate question ids"


def test_questions_reference_real_task_statements():
    for q in QUESTIONS:
        assert q["task_statement"] in TASK_IDS, q["id"]
        assert q["domain"] == TASK_DOMAIN[q["task_statement"]], q["id"]


def test_question_options_are_A_B_C_D():
    for q in QUESTIONS:
        keys = [o["key"] for o in q["options"]]
        assert keys == ["A", "B", "C", "D"], q["id"]


def test_correct_answer_is_a_real_option():
    for q in QUESTIONS:
        keys = {o["key"] for o in q["options"]}
        assert q["correct"] in keys, q["id"]


def test_every_distractor_has_a_rationale():
    for q in QUESTIONS:
        expected = {"A", "B", "C", "D"} - {q["correct"]}
        got = set(q["rationale"]["distractors"].keys())
        assert got == expected, f"{q['id']}: distractor rationales {got} != {expected}"


def test_question_lab_links_resolve():
    for q in QUESTIONS:
        if q.get("lab"):
            assert (LABS_ROOT / q["lab"]).is_dir(), f"{q['id']} → missing lab {q['lab']}"


# --------------------------------------------------------------------------- #
# Flashcard & concept integrity                                                #
# --------------------------------------------------------------------------- #
def test_flashcard_ids_unique_and_reference_real_tasks():
    ids = [f["id"] for f in FLASHCARDS]
    assert len(ids) == len(set(ids)), "duplicate flashcard ids"
    for f in FLASHCARDS:
        assert f["task_statement"] in TASK_IDS, f["id"]
        assert f["domain"] == TASK_DOMAIN[f["task_statement"]], f["id"]


def test_concepts_reference_real_tasks_and_labs():
    for c in CONCEPTS:
        assert c["task_statement"] in TASK_IDS, c["task_statement"]
        assert c["domain"] == TASK_DOMAIN[c["task_statement"]], c["task_statement"]
        if c.get("lab"):
            assert (LABS_ROOT / c["lab"]).is_dir(), f"{c['task_statement']} → missing lab {c['lab']}"


def test_concepts_have_at_most_one_per_task_statement():
    seen = [c["task_statement"] for c in CONCEPTS]
    assert len(seen) == len(set(seen)), "more than one concept per task statement"


# --------------------------------------------------------------------------- #
# Labs index (generated by tools/build_labs.py)                                #
# --------------------------------------------------------------------------- #
def test_labs_cover_every_lab_dir():
    lab_dirs = sorted(d.name for d in LABS_ROOT.glob("lab-*") if d.is_dir())
    indexed = sorted(l["slug"] for l in LABS)
    assert indexed == lab_dirs, f"labs.json out of sync with labs/ — run tools/build_labs.py"


def test_labs_slugs_resolve_and_have_content():
    for l in LABS:
        assert (LABS_ROOT / l["slug"]).is_dir(), l["slug"]
        assert l["readme_html"].strip(), f"{l['slug']} has empty readme_html"


# --------------------------------------------------------------------------- #
# Coverage (gated by PILOT_DOMAINS)                                            #
# --------------------------------------------------------------------------- #
def test_question_coverage_meets_target_for_pilot_domains():
    target = META["config"]["questions_per_task_target"]
    counts: dict[str, int] = {tid: 0 for tid in TASK_IDS}
    for q in QUESTIONS:
        counts[q["task_statement"]] += 1
    shortfalls = {
        tid: counts[tid]
        for tid in TASK_IDS
        if TASK_DOMAIN[tid] in PILOT_DOMAINS and counts[tid] < target
    }
    assert not shortfalls, f"task statements below target {target}: {shortfalls}"


def test_pilot_domains_have_a_concept_per_task_statement():
    have = {c["task_statement"] for c in CONCEPTS}
    missing = {
        tid for tid in TASK_IDS
        if TASK_DOMAIN[tid] in PILOT_DOMAINS and tid not in have
    }
    assert not missing, f"missing concept explainers for: {sorted(missing)}"
