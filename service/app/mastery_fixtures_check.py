"""Fixture check for mastery.py against shared/mastery-fixtures.json —
the Python half of the twin contract (run: python -m app.mastery_fixtures_check)."""

from __future__ import annotations

import json

from . import db, mastery

FIXTURES = db.REPO_ROOT / "shared" / "mastery-fixtures.json"


def main() -> None:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    failures = []

    for case in fixtures["apply_review"]:
        got = mastery.apply_review(case["args"]["score"], case["args"]["rating"])
        if abs(got - case["expected"]) >= 1e-9:
            failures.append(f"apply_review{case['args']} = {got}, want {case['expected']}")

    for case in fixtures["apply_decay"]:
        got = mastery.apply_decay(case["args"]["score"], case["args"]["days"])
        if abs(got - case["expected"]) >= 1e-9:
            failures.append(f"apply_decay{case['args']} = {got}, want {case['expected']}")

    for case in fixtures["lesson_mastered"]:
        a = case["args"]
        got = mastery.lesson_mastered(
            a["deck_stats"], a["concept_scores"], a["retention_threshold"], a["concept_threshold"]
        )
        if got != case["expected"]:
            failures.append(f"lesson_mastered{a} = {got}, want {case['expected']}")

    total = sum(len(fixtures[k]) for k in ("apply_review", "apply_decay", "lesson_mastered"))
    if failures:
        raise SystemExit("FIXTURE FAILURES:\n  " + "\n  ".join(failures))
    print(f"mastery fixtures: {total}/{total} pass (python)")


if __name__ == "__main__":
    main()
