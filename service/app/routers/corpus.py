"""Read-only corpus endpoints. Refs use SBL abbreviations: John.1.1"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db

router = APIRouter(prefix="/api/corpus", tags=["corpus"])


def _token_dict(row) -> dict:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": row["chapter"],
        "verse": row["verse"],
        "pos": row["pos"],
        "surface": row["surface"],
        "normalized": row["normalized"],
        "lemma": row["lemma"],
        "parse": row["parse"],
        "gloss": row["gloss"],
    }


@router.get("/info")
def info() -> list[dict]:
    conn = db.get_conn()
    try:
        corpora = [dict(r) for r in conn.execute("select * from corpora").fetchall()]
        for c in corpora:
            c["tokens"] = conn.execute(
                "select count(*) as n from corpus_tokens where corpus_id = ?", (c["id"],)
            ).fetchone()["n"]
        return corpora
    finally:
        conn.close()


@router.get("/ref/{ref}")
def by_ref(ref: str, corpus_id: str = "sblgnt") -> dict:
    try:
        book, chapter, verse = ref.split(".")
        chapter_n, verse_n = int(chapter), int(verse)
    except ValueError:
        raise HTTPException(422, "ref format: Book.Chapter.Verse e.g. John.1.1")
    conn = db.get_conn()
    try:
        rows = conn.execute(
            """
            select * from corpus_tokens
            where corpus_id = ? and book = ? and chapter = ? and verse = ?
            order by pos
            """,
            (corpus_id, book, chapter_n, verse_n),
        ).fetchall()
        if not rows:
            raise HTTPException(404, f"no tokens for {ref} — check book abbreviation (e.g. John, Matt, 1Cor)")
        return {"ref": ref, "tokens": [_token_dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/lemmas")
def lemma_slice(rank_from: int = 1, rank_to: int = 50, corpus_id: str = "sblgnt") -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            """
            select lemma, count, rank from lemma_freq
            where corpus_id = ? and rank between ? and ?
            order by rank, lemma
            """,
            (corpus_id, rank_from, rank_to),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/lemma/{lemma}")
def by_lemma(lemma: str, limit: int = 50, corpus_id: str = "sblgnt") -> dict:
    conn = db.get_conn()
    try:
        normalized = db.nfc(lemma)
        rows = conn.execute(
            """
            select * from corpus_tokens
            where corpus_id = ? and lemma = ?
            order by id limit ?
            """,
            (corpus_id, normalized, limit),
        ).fetchall()
        total = conn.execute(
            "select count(*) as n from corpus_tokens where corpus_id = ? and lemma = ?",
            (corpus_id, normalized),
        ).fetchone()["n"]
        return {"lemma": normalized, "total": total, "tokens": [_token_dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/books")
def books(corpus_id: str = "sblgnt") -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            """
            select book, max(chapter) as chapters
            from corpus_tokens where corpus_id = ?
            group by book order by min(id)
            """,
            (corpus_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
