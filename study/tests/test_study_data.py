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
import re
import tomllib
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
QUESTIONS_STANDARD = _load(DATA / "questions-standard.json")
QUESTIONS_INTERMEDIATE = _load(DATA / "questions-intermediate.json")
QUESTIONS_HARD = _load(DATA / "questions-hard.json")
QUESTIONS_ALL = QUESTIONS_STANDARD + QUESTIONS_INTERMEDIATE + QUESTIONS_HARD
FLASHCARDS = _load(DATA / "flashcards.json")
CONCEPTS = _load(DATA / "concepts.json")
LABS = _load(DATA / "labs.json")
SETS = _load(DATA / "sets.json")
TASK_IDS = {ts["id"] for ts in META["task_statements"]}
TASK_DOMAIN = {ts["id"]: ts["domain"] for ts in META["task_statements"]}


# --------------------------------------------------------------------------- #
# Schema validation                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "data_file, schema_file",
    [
        ("meta.json", "meta.schema.json"),
        ("questions-standard.json", "questions.schema.json"),
        ("questions-intermediate.json", "questions.schema.json"),
        ("questions-hard.json", "questions.schema.json"),
        ("flashcards.json", "flashcards.schema.json"),
        ("concepts.json", "concepts.schema.json"),
        ("labs.json", "labs.schema.json"),
        ("sets.json", "sets.schema.json"),
    ],
)
def test_data_matches_schema(data_file, schema_file):
    data = _load(DATA / data_file)
    schema = _load(SCHEMA / schema_file)
    jsonschema.validate(instance=data, schema=schema)


# --------------------------------------------------------------------------- #
# Version consistency — meta.json's config.app_version is the single source   #
# of truth; pyproject.toml and serve.py must not silently drift from it.      #
# --------------------------------------------------------------------------- #
def test_app_version_matches_pyproject():
    pyproject = tomllib.loads((STUDY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == META["config"]["app_version"]


def test_app_version_matches_serve_py():
    serve_py = (STUDY_ROOT / "serve.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', serve_py, re.MULTILINE)
    assert match, "serve.py must define __version__ = \"X.Y.Z\""
    assert match.group(1) == META["config"]["app_version"]


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
# Question integrity — across all three difficulty tiers combined, since IDs   #
# must stay globally unique (progress history is keyed by bare id) and every   #
# tier must meet the same structural bar, not just Standard.                  #
# --------------------------------------------------------------------------- #
def test_question_ids_unique():
    ids = [q["id"] for q in QUESTIONS_ALL]
    assert len(ids) == len(set(ids)), "duplicate question ids across tiers"


def test_questions_reference_real_task_statements():
    for q in QUESTIONS_ALL:
        assert q["task_statement"] in TASK_IDS, q["id"]
        assert q["domain"] == TASK_DOMAIN[q["task_statement"]], q["id"]


def test_question_options_are_A_B_C_D():
    for q in QUESTIONS_ALL:
        keys = [o["key"] for o in q["options"]]
        assert keys == ["A", "B", "C", "D"], q["id"]


def test_correct_answer_is_a_real_option():
    for q in QUESTIONS_ALL:
        keys = {o["key"] for o in q["options"]}
        assert q["correct"] in keys, q["id"]


def test_every_distractor_has_a_rationale():
    for q in QUESTIONS_ALL:
        expected = {"A", "B", "C", "D"} - {q["correct"]}
        got = set(q["rationale"]["distractors"].keys())
        assert got == expected, f"{q['id']}: distractor rationales {got} != {expected}"


def test_question_lab_links_resolve():
    for q in QUESTIONS_ALL:
        if q.get("lab"):
            assert (LABS_ROOT / q["lab"]).is_dir(), f"{q['id']} → missing lab {q['lab']}"


def test_each_tier_meets_minimum_question_count():
    tiers = {
        "questions-standard.json": QUESTIONS_STANDARD,
        "questions-intermediate.json": QUESTIONS_INTERMEDIATE,
        "questions-hard.json": QUESTIONS_HARD,
    }
    shortfalls = {name: len(qs) for name, qs in tiers.items() if len(qs) < 50}
    assert not shortfalls, f"tiers below the 50-question minimum: {shortfalls}"


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
# Set manifest (Web UI's dynamic set picker) — every listed file must exist,  #
# and every questions-*.json / flashcards*.json file on disk must be listed,  #
# so a new tier/set can never silently go unregistered.                       #
# --------------------------------------------------------------------------- #
def test_set_manifest_files_exist():
    for kind in ("questions", "flashcards"):
        for entry in SETS[kind]:
            assert (DATA / entry["file"]).is_file(), f"{kind} set {entry['id']!r} → missing {entry['file']}"


def test_set_manifest_covers_every_question_and_flashcard_file_on_disk():
    listed = {entry["file"] for entry in SETS["questions"]}
    on_disk = {p.name for p in DATA.glob("questions*.json")}
    assert on_disk == listed, f"sets.json out of sync with study/data/ — on disk {on_disk}, listed {listed}"

    listed = {entry["file"] for entry in SETS["flashcards"]}
    on_disk = {p.name for p in DATA.glob("flashcards*.json")}
    assert on_disk == listed, f"sets.json out of sync with study/data/ — on disk {on_disk}, listed {listed}"


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
    # Scoped to the Standard tier only — the per-task target was calibrated
    # against it; Intermediate/Hard have their own (lower, still-being-built)
    # coverage bars tracked separately (see BL-031 in BACKLOG.md).
    target = META["config"]["questions_per_task_target"]
    counts: dict[str, int] = {tid: 0 for tid in TASK_IDS}
    for q in QUESTIONS_STANDARD:
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
