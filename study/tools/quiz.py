#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""A colorful, offline terminal quiz runner for CCAF-style practice question sets.

Reads one or more JSON files matching the schema of study/data/questions.json
(scenario, stem, four options, correct key, rationale, domain, task_statement,
difficulty, tags), runs an interactive multiple-choice session in the
terminal, and tracks personal correct/incorrect results across sessions in a
small local JSON history file so you can see progress over time and re-drill
whatever you've missed.
"""

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"

# Personal progress is scratch state, not project content, so it defaults into
# the repo's gitignored .working/ directory (study/tools/ -> study/ -> repo root)
# rather than living next to this tracked script.
DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / ".working" / "quiz_history.json"
HISTORY_SCHEMA_VERSION = 1


# --------------------------------------------------------------------------
# Color
# --------------------------------------------------------------------------

class Color:
    """Minimal ANSI helper. Disabled automatically when not a TTY or via --no-color."""

    enabled = True

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"

    @classmethod
    def wrap(cls, text, *codes):
        if not cls.enabled:
            return text
        return "".join(codes) + text + cls.RESET


def c(text, *codes):
    return Color.wrap(text, *codes)


def rule(char="─", width=72, color=Color.DIM):
    print(c(char * width, color))


def bar(pct, width=24):
    """A small colored proportion bar for percentages (0-100)."""
    filled = round(width * max(0.0, min(100.0, pct)) / 100)
    color = Color.GREEN if pct >= 80 else Color.YELLOW if pct >= 60 else Color.RED
    return c("█" * filled, color) + c("░" * (width - filled), Color.DIM)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

@dataclass
class Question:
    id: str
    domain: int
    task_statement: str
    stem: str
    options: list
    correct: str
    rationale: dict
    source: str
    scenario: Optional[str] = None
    lab: Optional[str] = None
    difficulty: Optional[int] = None
    tags: list = field(default_factory=list)


def load_questions(paths):
    """Load and merge one or more questions.json-schema files, tagging each
    question with the basename of the file it came from."""
    questions = []
    seen_ids = {}
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: could not read {path}: {exc}")
        if not isinstance(raw, list):
            raise SystemExit(f"error: {path} does not contain a JSON array of questions")
        for item in raw:
            try:
                q = Question(
                    id=item["id"],
                    domain=item["domain"],
                    task_statement=item["task_statement"],
                    stem=item["stem"],
                    options=item["options"],
                    correct=item["correct"],
                    rationale=item["rationale"],
                    source=path.name,
                    scenario=item.get("scenario"),
                    lab=item.get("lab"),
                    difficulty=item.get("difficulty"),
                    tags=item.get("tags") or [],
                )
            except KeyError as exc:
                raise SystemExit(f"error: {path} has a question missing required field {exc}")
            if q.id in seen_ids:
                print(
                    c(f"warning: duplicate question id {q.id!r} in {path.name} "
                      f"(already loaded from {seen_ids[q.id]}); keeping the first one", Color.YELLOW),
                    file=sys.stderr,
                )
                continue
            seen_ids[q.id] = path.name
            questions.append(q)
    return questions


# --------------------------------------------------------------------------
# History (cumulative, cross-session progress tracking)
# --------------------------------------------------------------------------

def load_history(path):
    if not path.exists():
        return {"version": HISTORY_SCHEMA_VERSION, "questions": {}, "sessions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print(c(f"warning: {path} is not valid JSON; starting a fresh history", Color.YELLOW), file=sys.stderr)
        return {"version": HISTORY_SCHEMA_VERSION, "questions": {}, "sessions": []}
    data.setdefault("version", HISTORY_SCHEMA_VERSION)
    data.setdefault("questions", {})
    data.setdefault("sessions", [])
    return data


def save_history(path, history):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def record_answer(history, question, correct):
    entry = history["questions"].setdefault(
        question.id, {"attempts": 0, "correct": 0, "last_result": None, "last_seen": None, "source": question.source}
    )
    entry["attempts"] += 1
    entry["correct"] += 1 if correct else 0
    entry["last_result"] = "correct" if correct else "incorrect"
    entry["last_seen"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry["source"] = question.source


def record_session(history, *, source_files, filters, total, correct, duration_seconds):
    history["sessions"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_files": source_files,
        "filters": filters,
        "total": total,
        "correct": correct,
        "score_pct": round(100 * correct / total, 1) if total else 0.0,
        "duration_seconds": round(duration_seconds, 1),
    })


# --------------------------------------------------------------------------
# Filtering & selection
# --------------------------------------------------------------------------

def apply_filters(questions, args, history):
    pool = questions
    if args.domain is not None:
        pool = [q for q in pool if q.domain == args.domain]
    if args.task is not None:
        pool = [q for q in pool if q.task_statement == args.task]
    if args.tag is not None:
        pool = [q for q in pool if args.tag in q.tags]
    if args.review_missed:
        missed_ids = {
            qid for qid, entry in history["questions"].items()
            if entry.get("last_result") == "incorrect"
        }
        pool = [q for q in pool if q.id in missed_ids]
    return pool


def select_questions(pool, args):
    pool = list(pool)
    if args.shuffle:
        rng = random.Random(args.seed) if args.seed is not None else random.Random()
        rng.shuffle(pool)
    if args.num is not None:
        pool = pool[: args.num]
    return pool


# --------------------------------------------------------------------------
# Interactive quiz session
# --------------------------------------------------------------------------

def print_banner():
    rule("═")
    print(c("  CCAF PRACTICE QUIZ", Color.BOLD, Color.CYAN))
    rule("═")


def print_question(index, total, q):
    print()
    header = f"Question {index}/{total}"
    tag = f"Domain {q.domain} · Task {q.task_statement}"
    if q.difficulty is not None:
        tag += f" · difficulty {q.difficulty}/10"
    print(c(header, Color.BOLD, Color.CYAN) + c("   " + tag, Color.DIM))
    rule()
    if q.scenario:
        print(c(q.scenario, Color.DIM))
        print()
    print(c(q.stem, Color.BOLD))
    print()
    for opt in q.options:
        print(f"  {c(opt['key'], Color.BOLD, Color.MAGENTA)}. {opt['text']}")
    print()


def prompt_answer(valid_keys):
    while True:
        raw = input(c("Your answer ", Color.CYAN) + c("(or 'skip', 'quit')", Color.DIM) + c(": ", Color.CYAN)).strip()
        low = raw.lower()
        if low in ("q", "quit", "exit"):
            return "quit"
        if low in ("s", "skip"):
            return "skip"
        up = raw.upper()
        if up in valid_keys:
            return up
        print(c(f"  Please enter one of {', '.join(valid_keys)}, or 'skip'/'quit'.", Color.YELLOW))


def show_feedback(q, chosen):
    correct = chosen == q.correct
    if correct:
        print(c("  ✓ Correct!", Color.BOLD, Color.GREEN))
    else:
        print(c(f"  ✗ Incorrect — correct answer is {q.correct}.", Color.BOLD, Color.RED))
    print()
    print(c("  Why: ", Color.BOLD) + q.rationale.get("correct", ""))
    if not correct:
        distractor = q.rationale.get("distractors", {}).get(chosen)
        if distractor:
            print(c(f"  About {chosen}: ", Color.BOLD) + distractor)
    if q.lab:
        print(c(f"  Practice: {q.lab}", Color.DIM))
    return correct


def run_session(questions, history, history_path, source_files, filters):
    print_banner()
    print(c(f"  {len(questions)} question(s) loaded — answer A-D, or 'skip' / 'quit' anytime.\n", Color.DIM))
    start = datetime.now()
    correct_count = 0
    answered = 0
    for i, q in enumerate(questions, start=1):
        print_question(i, len(questions), q)
        valid_keys = [o["key"] for o in q.options]
        choice = prompt_answer(valid_keys)
        if choice == "quit":
            print(c("\nEnding session early.", Color.YELLOW))
            break
        if choice == "skip":
            print(c("  Skipped.", Color.DIM))
            continue
        answered += 1
        is_correct = show_feedback(q, choice)
        if is_correct:
            correct_count += 1
        record_answer(history, q, is_correct)
        running_pct = 100 * correct_count / answered
        print(c(f"\n  Score so far: {correct_count}/{answered} ({running_pct:.0f}%)", Color.DIM))

    duration = (datetime.now() - start).total_seconds()
    if answered:
        record_session(
            history,
            source_files=source_files,
            filters=filters,
            total=answered,
            correct=correct_count,
            duration_seconds=duration,
        )
        save_history(history_path, history)
    print_summary(correct_count, answered, duration)


def print_summary(correct_count, answered, duration_seconds):
    print()
    rule("═")
    print(c("  SESSION SUMMARY", Color.BOLD, Color.CYAN))
    rule("═")
    if answered == 0:
        print(c("  No questions were answered.", Color.YELLOW))
        return
    pct = 100 * correct_count / answered
    print(f"  Score: {c(f'{correct_count}/{answered}', Color.BOLD)}  {bar(pct)}  {pct:.0f}%")
    tier = (
        "Excellent" if pct >= 90 else
        "Solid" if pct >= 75 else
        "Keep practicing" if pct >= 60 else
        "Needs review"
    )
    tier_color = Color.GREEN if pct >= 75 else Color.YELLOW if pct >= 60 else Color.RED
    print(f"  {c(tier, Color.BOLD, tier_color)}")
    minutes, seconds = divmod(int(duration_seconds), 60)
    print(c(f"  Time: {minutes}m {seconds}s", Color.DIM))
    print()


# --------------------------------------------------------------------------
# Stats / list modes (no quiz — inspect data)
# --------------------------------------------------------------------------

def print_stats(questions, history):
    by_id = {q.id: q for q in questions}
    print_banner()
    sessions = history["sessions"]
    if not sessions:
        print(c("\n  No recorded sessions yet — run a quiz first.\n", Color.YELLOW))
        return
    total_attempts = sum(e["attempts"] for e in history["questions"].values())
    total_correct = sum(e["correct"] for e in history["questions"].values())
    overall_pct = 100 * total_correct / total_attempts if total_attempts else 0.0
    print()
    print(f"  Sessions logged: {c(str(len(sessions)), Color.BOLD)}")
    print(f"  Total answers:   {c(str(total_attempts), Color.BOLD)}")
    print(f"  Overall accuracy: {bar(overall_pct)}  {overall_pct:.0f}%  ({total_correct}/{total_attempts})")

    by_domain = {}
    for qid, entry in history["questions"].items():
        q = by_id.get(qid)
        if q is None:
            continue
        d = by_domain.setdefault(q.domain, {"attempts": 0, "correct": 0})
        d["attempts"] += entry["attempts"]
        d["correct"] += entry["correct"]
    if by_domain:
        print()
        print(c("  By domain:", Color.BOLD))
        for domain in sorted(by_domain):
            d = by_domain[domain]
            pct = 100 * d["correct"] / d["attempts"] if d["attempts"] else 0.0
            print(f"    Domain {domain}  {bar(pct)}  {pct:5.1f}%  ({d['correct']}/{d['attempts']})")

    missed = [qid for qid, e in history["questions"].items() if e.get("last_result") == "incorrect"]
    print()
    print(c(f"  Currently missed (available to re-drill with --review-missed): {len(missed)}", Color.DIM))
    print()
    print(c("  Recent sessions:", Color.BOLD))
    for s in sessions[-5:]:
        print(f"    {s['timestamp']}  {s['correct']}/{s['total']} ({s['score_pct']}%)  {', '.join(s['source_files'])}")
    print()


def print_list(questions):
    by_domain = {}
    for q in questions:
        by_domain.setdefault(q.domain, {}).setdefault(q.task_statement, 0)
        by_domain[q.domain][q.task_statement] += 1
    print_banner()
    print()
    all_tags = sorted({t for q in questions for t in q.tags})
    for domain in sorted(by_domain):
        print(c(f"  Domain {domain}", Color.BOLD, Color.CYAN))
        for task in sorted(by_domain[domain], key=lambda t: [int(p) for p in t.split(".")]):
            print(f"    {task}: {by_domain[domain][task]} question(s)")
    print()
    print(c(f"  {len(questions)} question(s) total across {len(by_domain)} domain(s).", Color.DIM))
    if all_tags:
        print(c(f"  Tags seen: {', '.join(all_tags)}", Color.DIM))
    print()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

EPILOG = """\
Examples (run from the repo root):
  # Quiz on the main study bank, questions in file order
  uv run study/tools/quiz.py study/data/questions.json

  # Shuffle and cap the session at 20 random questions
  uv run study/tools/quiz.py study/data/questions.json --shuffle --num 20

  # Drill just one domain (Agentic Architecture & Orchestration)
  uv run study/tools/quiz.py study/data/questions.json --domain 1

  # Drill one task statement
  uv run study/tools/quiz.py study/data/questions.json --task 4.3

  # Filter by tag
  uv run study/tools/quiz.py study/data/questions.json --tag hooks

  # Combine the main bank with your own personal question set
  uv run study/tools/quiz.py study/data/questions.json .working/my-questions.json --shuffle

  # Re-drill only the questions you've gotten wrong before
  uv run study/tools/quiz.py study/data/questions.json --review-missed

  # Reproducible shuffle order (useful for comparing runs)
  uv run study/tools/quiz.py study/data/questions.json --shuffle --seed 42

  # View cumulative stats without starting a quiz
  uv run study/tools/quiz.py study/data/questions.json --stats

  # See what's available (domains/tasks/tags) in a file without quizzing
  uv run study/tools/quiz.py study/data/questions.json --list

  # Use a separate history file, e.g. to keep two question banks' progress apart
  uv run study/tools/quiz.py .working/my-questions.json --history .working/my-questions_history.json

  # Wipe saved progress for the current history file
  uv run study/tools/quiz.py study/data/questions.json --reset-history

  # Disable color (e.g. piping output to a file)
  uv run study/tools/quiz.py study/data/questions.json --no-color

  # Show the script version
  uv run study/tools/quiz.py --version
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="quiz.py",
        description="Interactive, offline terminal quiz runner for CCAF-style practice "
                    "question sets (questions.json schema), with cross-session progress tracking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "files", nargs="*", type=Path,
        help="One or more question-set JSON files (questions.json schema). "
             "Not required for --reset-history alone.",
    )
    parser.add_argument("--domain", type=int, metavar="N", help="Only include questions from domain N (1-5).")
    parser.add_argument("--task", metavar="X.Y", help="Only include questions from task statement X.Y (e.g. 4.3).")
    parser.add_argument("--tag", metavar="TAG", help="Only include questions with this tag.")
    parser.add_argument("--num", type=int, metavar="N", help="Limit the session to N questions.")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle question order before selecting.")
    parser.add_argument("--seed", type=int, metavar="N", help="Random seed for --shuffle, for reproducible order.")
    parser.add_argument(
        "--review-missed", action="store_true",
        help="Only include questions whose most recent recorded attempt was incorrect.",
    )
    parser.add_argument(
        "--history", type=Path, default=DEFAULT_HISTORY_PATH, metavar="PATH",
        help=f"Path to the progress-history JSON file (default: {DEFAULT_HISTORY_PATH}).",
    )
    parser.add_argument("--stats", action="store_true", help="Show cumulative stats and exit (no quiz).")
    parser.add_argument("--list", action="store_true", help="List domains/tasks/tags in the loaded file(s) and exit.")
    parser.add_argument("--reset-history", action="store_true", help="Delete all saved progress in --history and exit.")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip the confirmation prompt for --reset-history.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in output.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    Color.enabled = sys.stdout.isatty() and not args.no_color

    if args.reset_history:
        if args.history.exists():
            if not args.yes:
                answer = input(f"Delete all progress history in {args.history}? [y/N] ").strip().lower()
                if answer != "y":
                    print("Cancelled.")
                    return 0
            args.history.unlink()
            print(c(f"Deleted {args.history}.", Color.GREEN))
        else:
            print(c(f"No history file at {args.history}; nothing to delete.", Color.YELLOW))
        return 0

    if not args.files:
        parser.error("at least one question-set JSON file is required (see --help for examples)")

    missing = [p for p in args.files if not p.exists()]
    if missing:
        parser.error(f"file(s) not found: {', '.join(str(p) for p in missing)}")

    questions = load_questions(args.files)
    if not questions:
        raise SystemExit("error: no questions loaded from the given file(s)")

    history = load_history(args.history)
    pool = apply_filters(questions, args, history)

    if args.list:
        print_list(pool)
        return 0

    if args.stats:
        print_stats(pool, history)
        return 0

    if not pool:
        print(c("No questions match the given filters.", Color.YELLOW))
        return 1

    selected = select_questions(pool, args)
    if not selected:
        print(c("No questions left after applying --num.", Color.YELLOW))
        return 1

    filters = {
        "domain": args.domain, "task": args.task, "tag": args.tag,
        "review_missed": args.review_missed, "num": args.num, "shuffle": args.shuffle,
    }
    try:
        run_session(selected, history, args.history, [p.name for p in args.files], filters)
    except (KeyboardInterrupt, EOFError):
        print(c("\n\nInterrupted — progress so far was not saved for this session.", Color.YELLOW))
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
