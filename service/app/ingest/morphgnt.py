"""MorphGNT SBLGNT → SQLite ingest. Idempotent: wipes and reloads the
'sblgnt' corpus_id each run.

Source: https://github.com/morphgnt/sblgnt (cloned to data/morphgnt-sblgnt).
License, recorded at ingest per the master plan: the SBLGNT text is subject to
the SBLGNT EULA (http://sblgnt.com/license/); the morphological parsing and
lemmatization are CC-BY-SA 3.0. Citation: Tauber, J. K., ed. (2017)
"MorphGNT: SBLGNT Edition" Version 6.12, DOI 10.5281/zenodo.376200.

File format (one token per line, 7 space-separated columns):
  BBCCVV  pos  parse-code  text  word  normalized  lemma
Book code BB = NT book number (01=Matt … 27=Rev).

Run: scripts\\ingest-morphgnt.cmd  (or `python -m app.ingest.morphgnt` with
PYTHONPATH=service and PYTHONUTF8=1).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from .. import db

CORPUS_ID = "sblgnt"
CORPUS_NAME = "MorphGNT SBLGNT (Tauber, ed., v6.12)"
CORPUS_LICENSE = (
    "SBLGNT text: SBLGNT EULA (http://sblgnt.com/license/); "
    "morphological parsing + lemmatization: CC-BY-SA 3.0. "
    "Cite: Tauber, J. K., ed. (2017) MorphGNT: SBLGNT Edition, v6.12, "
    "DOI 10.5281/zenodo.376200"
)

SOURCE_DIR = db.REPO_ROOT / "data" / "morphgnt-sblgnt"

# SBL-style book abbreviations, indexed by MorphGNT book number (1-27)
BOOKS = [
    "Matt", "Mark", "Luke", "John", "Acts", "Rom", "1Cor", "2Cor", "Gal",
    "Eph", "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim", "Titus",
    "Phlm", "Heb", "Jas", "1Pet", "2Pet", "1John", "2John", "3John",
    "Jude", "Rev",
]


def parse_line(line: str) -> tuple | None:
    parts = line.split()
    if len(parts) != 7:
        return None
    ref, pos_code, parse_code, text, _word, normalized, lemma = parts
    book_n = int(ref[0:2])
    chapter = int(ref[2:4])
    verse = int(ref[4:6])
    return (
        BOOKS[book_n - 1],
        chapter,
        verse,
        db.nfc(text),
        db.nfc(normalized),
        db.nfc(lemma),
        f"{pos_code} {parse_code}",  # stored verbatim, both columns
    )


def ingest(source_dir: Path = SOURCE_DIR) -> dict:
    files = sorted(source_dir.glob("*-morphgnt.txt"))
    if not files:
        raise SystemExit(
            f"no MorphGNT files in {source_dir} — clone "
            "https://github.com/morphgnt/sblgnt there first "
            "(scripts\\ingest-morphgnt.cmd does this)"
        )

    conn = db.get_conn()
    try:
        conn.execute("delete from lemma_freq where corpus_id = ?", (CORPUS_ID,))
        conn.execute("delete from corpus_tokens where corpus_id = ?", (CORPUS_ID,))
        conn.execute("delete from corpora where id = ?", (CORPUS_ID,))
        conn.execute(
            "insert into corpora (id, name, license) values (?, ?, ?)",
            (CORPUS_ID, CORPUS_NAME, CORPUS_LICENSE),
        )

        token_count = 0
        for path in files:
            rows = []
            last_ref: tuple[str, int, int] | None = None
            pos_in_verse = 0
            for line in path.read_text(encoding="utf-8").splitlines():
                parsed = parse_line(line)
                if parsed is None:
                    continue
                book, chapter, verse, text, normalized, lemma, parse = parsed
                ref = (book, chapter, verse)
                pos_in_verse = pos_in_verse + 1 if ref == last_ref else 1
                last_ref = ref
                rows.append(
                    (CORPUS_ID, book, chapter, verse, pos_in_verse, text, normalized, lemma, parse)
                )
            conn.executemany(
                """
                insert into corpus_tokens
                  (corpus_id, book, chapter, verse, pos, surface, normalized, lemma, parse)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            token_count += len(rows)

        # frequency table: count per lemma, dense rank by count desc
        conn.execute(
            """
            insert into lemma_freq (corpus_id, lemma, count, rank)
            select corpus_id, lemma, count(*) as n,
                   dense_rank() over (order by count(*) desc)
            from corpus_tokens
            where corpus_id = ?
            group by lemma
            """,
            (CORPUS_ID,),
        )
        lemma_count = conn.execute(
            "select count(*) as n from lemma_freq where corpus_id = ?", (CORPUS_ID,)
        ).fetchone()["n"]
        conn.commit()
        return {"tokens": token_count, "lemmas": lemma_count, "files": len(files)}
    finally:
        conn.close()


if __name__ == "__main__":
    if sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        raise SystemExit("run with PYTHONUTF8=1 (see scripts/ingest-morphgnt.cmd)")
    db.bootstrap()
    started = time.time()
    result = ingest()
    print(
        f"ingested {result['tokens']} tokens, {result['lemmas']} lemmas "
        f"from {result['files']} files in {time.time() - started:.1f}s"
    )
