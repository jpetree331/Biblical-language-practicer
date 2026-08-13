"""Syllabus-map loader: data/syllabus_map.<lang>.json → concepts + stub
lessons.

Guardrails (per plan, enforced here):
- PD-only: a map with "source_is_pd": false may NOT have in-app source_texts —
  if such rows exist for its reading_refs the loader refuses outright. This is
  what keeps the future Dobson/Hebrew map honest by construction.
- Typo guard: any vocab lemma absent from the corpus is a hard error with a
  friendly near-match listing.
- Unreviewed chapters load, but LOUDLY: every "reviewed": false chapter is
  warned about (the draft is Jess-reviewed, not machine-trusted).
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from . import db
from .gen.syllabus import near_matches


class CurriculumError(Exception):
    pass


def load_map(map_doc: dict) -> dict:
    chapters = map_doc.get("chapters") or []
    if not chapters:
        raise CurriculumError("map has no chapters")
    source_is_pd = bool(map_doc.get("source_is_pd"))

    conn = db.get_conn()
    try:
        # -- PD guardrail ---------------------------------------------------
        if not source_is_pd:
            refs = [c.get("reading_ref") for c in chapters if c.get("reading_ref")]
            for ref in refs:
                row = conn.execute(
                    "select 1 from source_texts where ref = ?", (ref,)
                ).fetchone()
                if row:
                    raise CurriculumError(
                        f"REFUSED: map declares source_is_pd=false but in-app "
                        f"source text exists for {ref!r}. Non-PD books get "
                        f"pointer-only reading items — delete the source_texts "
                        f"row or fix the map."
                    )

        # -- lemma typo guard (hard error, near-match help) ------------------
        problems: list[str] = []
        for ch in chapters:
            for lemma in ch.get("vocab_lemmas", []):
                lemma_n = db.nfc(lemma)
                hit = conn.execute(
                    "select 1 from lemma_freq where corpus_id='sblgnt' and lemma=?",
                    (lemma_n,),
                ).fetchone()
                if not hit:
                    cands = near_matches(conn, lemma_n)
                    hint = f" — did you mean: {', '.join(cands)}?" if cands else ""
                    problems.append(f"chapter {ch.get('n')}: lemma {lemma!r} not in corpus{hint}")
        if problems:
            raise CurriculumError("lemma validation failed:\n  " + "\n  ".join(problems))

        # -- populate -------------------------------------------------------
        warnings: list[str] = []
        for ch in chapters:
            if not ch.get("reviewed"):
                warnings.append(
                    f"chapter {ch['n']} ({ch.get('title', '?')}) is UNREVIEWED — "
                    f"drafted by a model, not yet checked by you"
                )
            for concept in ch.get("concepts", []):
                conn.execute(
                    """
                    insert into concepts (id, name, chapter_ref) values (?, ?, ?)
                    on conflict(id) do update set name=excluded.name
                    """,
                    (concept["id"], concept["name"], ch.get("reading_ref")),
                )
            existing = conn.execute(
                "select id from lessons where seq = ?", (ch["n"],)
            ).fetchone()
            if existing is None:
                lesson_id = str(uuid.uuid4())
                conn.execute(
                    "insert into lessons (id, seq, title, chapter_ref, status) values (?, ?, ?, ?, ?)",
                    (
                        lesson_id,
                        ch["n"],
                        ch.get("title") or f"Lesson {ch['n']}",
                        ch.get("reading_ref"),
                        "active" if ch["n"] == 1 else "locked",
                    ),
                )
            else:
                lesson_id = existing["id"]
                conn.execute(
                    "update lessons set title = ?, chapter_ref = ? where seq = ?",
                    (ch.get("title") or f"Lesson {ch['n']}", ch.get("reading_ref"), ch["n"]),
                )

            # lesson items: read → drill(vocab) → drill(parsing) → translate →
            # compose. Drill refs use a deckname: convention resolved at read
            # time, so build-chapter can run before or after loading.
            conn.execute("delete from lesson_items where lesson_id = ?", (lesson_id,))
            items = [("read", ch.get("reading_ref") or f"chapter:{ch['n']}")]
            if ch.get("vocab_lemmas"):
                items.append(("drill", f"deckname:Greek ch.{ch['n']} vocab"))
                items.append(("drill", f"deckname:Greek ch.{ch['n']} parsing"))
            items.append(("translate", "pending"))
            items.append(("compose", "pending"))
            for seq, (kind, ref) in enumerate(items, start=1):
                conn.execute(
                    "insert into lesson_items (id, lesson_id, kind, ref, seq) values (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), lesson_id, kind, ref, seq),
                )
        conn.commit()
        n_concepts = conn.execute("select count(*) as n from concepts").fetchone()["n"]
        n_lessons = conn.execute("select count(*) as n from lessons").fetchone()["n"]
        return {"chapters": len(chapters), "concepts": n_concepts, "lessons": n_lessons,
                "warnings": warnings}
    finally:
        conn.close()


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else db.REPO_ROOT / "data" / "syllabus_map.greek.json"
    db.bootstrap()
    doc = json.loads(path.read_text(encoding="utf-8"))
    result = load_map(doc)
    for w in result["warnings"]:
        print(f"WARNING: {w}")
    print(
        f"loaded {result['chapters']} chapters -> {result['concepts']} concepts, "
        f"{result['lessons']} lesson rows ({len(result['warnings'])} unreviewed)"
    )


if __name__ == "__main__":
    main()
