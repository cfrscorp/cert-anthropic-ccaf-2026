#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate the labeled ``validation_set.json`` for Lab 18.

The set is engineered so that the *aggregate* extraction accuracy is high
(~97%) while one document-type segment (``handwritten_note``) performs poorly
(~70%). Two of the wrong handwritten extractions are deliberately assigned
HIGH confidence (miscalibration), so that:

  * a naive "trust everything above 0.9" policy still auto-accepts errors, and
  * stratified sampling of high-confidence extractions is needed to surface the
    masked, poorly-performing segment.

Every value is drawn from a SEEDED RNG so the output is byte-for-byte
reproducible and the lab tests stay deterministic.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

__version__ = "1.0.0"

# doc_type -> (field names, n_correct, n_wrong)
SPECS = [
    ("invoice", ["vendor", "total", "invoice_date"], 60, 0),
    ("receipt", ["merchant", "amount", "purchase_date"], 30, 0),
    ("handwritten_note", ["author", "body", "note_date"], 7, 3),
]


def build(seed: int) -> list[dict]:
    rng = random.Random(seed)

    def hi() -> float:  # confident and (usually) correct
        return round(rng.uniform(0.93, 0.99), 3)

    def mid() -> float:  # handwriting: harder OCR, still often right
        return round(rng.uniform(0.85, 0.96), 3)

    def low() -> float:  # genuinely uncertain
        return round(rng.uniform(0.58, 0.78), 3)

    records: list[dict] = []
    for doc_type, fields, n_correct, n_wrong in SPECS:
        conf_fn = mid if doc_type == "handwritten_note" else hi
        idx = 0
        for _ in range(n_correct):
            idx += 1
            records.append(
                {
                    "doc_id": f"{doc_type}-{idx:03d}",
                    "doc_type": doc_type,
                    "confidences": {f: conf_fn() for f in fields},
                    "ambiguous": False,
                    "contradictory": False,
                    "correct": True,
                }
            )
        for w in range(n_wrong):
            idx += 1
            if w < 2:
                # MISCALIBRATED: wrong but high confidence -> the dangerous,
                # masked case that stratified sampling must catch.
                confs = {f: round(rng.uniform(0.92, 0.96), 3) for f in fields}
                ambiguous = contradictory = False
            else:
                # Honestly uncertain / contradictory source -> routing catches it.
                confs = {f: (low() if f == fields[1] else mid()) for f in fields}
                ambiguous = False
                contradictory = True
            records.append(
                {
                    "doc_id": f"{doc_type}-{idx:03d}",
                    "doc_type": doc_type,
                    "confidences": confs,
                    "ambiguous": ambiguous,
                    "contradictory": contradictory,
                    "correct": False,
                }
            )
    return records


def summarize(records: list[dict]) -> str:
    total = len(records)
    correct = sum(1 for r in records if r["correct"])
    by_type: dict[str, list[int]] = {}
    for r in records:
        c, n = by_type.setdefault(r["doc_type"], [0, 0])
        by_type[r["doc_type"]] = [c + (1 if r["correct"] else 0), n + 1]
    lines = [f"total={total} aggregate_accuracy={correct / total:.3f}"]
    for t, (c, n) in sorted(by_type.items()):
        lines.append(f"  {t:18s} {c}/{n} = {c / n:.3f}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="make_validation_set.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Regenerate validation_set.json next to this script\n"
            "  uv run make_validation_set.py\n\n"
            "  # Print the accuracy summary without writing the file\n"
            "  uv run make_validation_set.py --stats-only\n\n"
            "  # Use a different seed and output path\n"
            "  uv run make_validation_set.py --seed 7 --out /tmp/vs.json\n\n"
            "  # Show version\n"
            "  uv run make_validation_set.py --version\n"
        ),
    )
    parser.add_argument("--seed", type=int, default=1818, help="RNG seed (default: 1818).")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "validation_set.json",
        help="Output JSON path (default: ./validation_set.json).",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Print the accuracy-by-segment summary and do not write any file.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    records = build(args.seed)
    print(summarize(records), file=sys.stderr)
    if args.stats_only:
        return 0
    args.out.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} records -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
