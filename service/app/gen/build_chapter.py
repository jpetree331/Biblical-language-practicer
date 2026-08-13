"""Build a reviewed chapter's decks via the Sprint 5 pipeline.

  python -m app.gen.build_chapter greek 3
  (scripts\\build-chapter.cmd greek 3)

Vocab deck: the chapter's own lemmas. Parsing deck: tokens matching the
chapter's verb concepts, restricted to lemmas introduced in chapters 1..N —
new grammar practiced on known words.

Refuses unreviewed chapters unless --force (the draft is Jess-reviewed;
building decks from an unreviewed draft defeats the review gate).
"""

from __future__ import annotations

import argparse
import json

import anyio

from .. import db
from . import pipeline

# GK.<TENSE>.<VOICE>.<MOOD> → MorphGNT parse LIKE pattern fragments
TENSE = {"PRES": "P", "IMPF": "I", "FUT": "F", "AOR": "A", "AOR2": "A", "PERF": "X", "PLUP": "Y"}
VOICE = {"ACT": "A", "MID": "M", "PASS": "P"}
MOOD = {"IND": "I", "SUBJ": "S", "IMPV": "D", "INF": "N", "PTCP": "P"}


def concept_to_pattern(concept_id: str) -> str | None:
    """GK.PRES.ACT.IND → 'V- _PAI%'. Non-verb concepts return None (no drill)."""
    parts = concept_id.split(".")
    if len(parts) != 4 or parts[0] != "GK":
        return None
    tense, voice, mood = parts[1], parts[2], parts[3]
    if tense not in TENSE or mood not in MOOD:
        return None
    if voice == "MP":  # middle/passive: two patterns won't fit one LIKE — use either
        return f"V- _{TENSE[tense]}_{MOOD[mood]}%"
    if voice not in VOICE:
        return None
    return f"V- _{TENSE[tense]}{VOICE[voice]}{MOOD[mood]}%"


async def build(language: str, n: int, force: bool) -> dict:
    map_path = db.REPO_ROOT / "data" / f"syllabus_map.{language}.json"
    doc = json.loads(map_path.read_text(encoding="utf-8"))
    chapters = {c["n"]: c for c in doc["chapters"]}
    if n not in chapters:
        raise SystemExit(f"no chapter {n} in {map_path.name}")
    chapter = chapters[n]
    if not chapter.get("reviewed") and not force:
        raise SystemExit(
            f"chapter {n} is not reviewed yet — review it in {map_path.name}, flip "
            f'"reviewed": true, and re-run (or pass --force to build from the draft).'
        )

    known_lemmas = sorted(
        {lem for m in range(1, n + 1) for lem in chapters.get(m, {}).get("vocab_lemmas", [])}
    )
    results = []

    if chapter.get("vocab_lemmas"):
        results.append(
            await pipeline.run_batch(
                {
                    "kind": "vocab_lemmas",
                    "lemmas": chapter["vocab_lemmas"],
                    "deck": f"Greek ch.{n} vocab",
                }
            )
        )

    patterns = [
        (c["id"], concept_to_pattern(c["id"]))
        for c in chapter.get("concepts", [])
    ]
    drillable = [(cid, p) for cid, p in patterns if p]
    for cid, pattern in drillable:
        try:
            results.append(
                await pipeline.run_batch(
                    {
                        "kind": "parsing_filtered",
                        "parse_like": pattern,
                        "lemma_in": known_lemmas,
                        "max_cards": 15,
                        "deck": f"Greek ch.{n} parsing",
                    }
                )
            )
        except ValueError as e:
            results.append({"concept": cid, "skipped": str(e)})

    return {
        "chapter": n,
        "title": chapter.get("title"),
        "known_lemmas": len(known_lemmas),
        "drillable_concepts": [cid for cid, _ in drillable],
        "batches": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.gen.build_chapter")
    parser.add_argument("language")
    parser.add_argument("chapter", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    db.bootstrap()
    result = anyio.run(build, args.language, args.chapter, args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
