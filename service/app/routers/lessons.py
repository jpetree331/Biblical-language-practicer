"""Lessons API — the spiral made visible.

Mastery evaluation happens on read: an active lesson whose decks are all at
review state with retention >= threshold, and whose concepts score >= 0.8
(after decay), flips to mastered and unlocks the next lesson. Manual override
always wins — Jess outranks the model of her own mastery (Rule: the deck core
stays topic-agnostic; this router only consumes generic deck stats and the
concept_mastery table)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db, mastery, scheduler

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def _deck_by_name(conn, name: str):
    return conn.execute(
        "select * from decks where name = ? and deleted_at is null", (name,)
    ).fetchone()


def _deck_mastery_stats(conn, deck_id: str, deck_config: dict) -> dict:
    total = conn.execute(
        "select count(*) as n from cards c join card_state s on s.card_id=c.id "
        "where c.deck_id=? and c.deleted_at is null",
        (deck_id,),
    ).fetchone()["n"]
    at_review = conn.execute(
        "select count(*) as n from cards c join card_state s on s.card_id=c.id "
        "where c.deck_id=? and c.deleted_at is null and s.state='review'",
        (deck_id,),
    ).fetchone()["n"]
    stats = scheduler.deck_stats(conn, deck_id)
    return {
        "all_review": total > 0 and at_review == total,
        "retention": stats["retention"],
        "due": stats["due"],
        "new": stats["new"],
        "total": total,
        "retention_threshold": float(deck_config.get("retentionThreshold", 0.9)),
    }


def _days_since(iso: str | None) -> float:
    if not iso:
        return 0.0
    then = datetime.fromisoformat(iso)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - then).total_seconds() / 86400.0)


def _concept_scores(conn, chapter_ref: str | None) -> list[dict]:
    if not chapter_ref:
        return []
    rows = conn.execute(
        """
        select c.id, c.name, m.score, m.updated_at
        from concepts c left join concept_mastery m on m.concept_id = c.id
        where c.chapter_ref = ?
        order by c.id
        """,
        (chapter_ref,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "score": mastery.apply_decay(r["score"] or 0.0, _days_since(r["updated_at"])),
            # evidence = a concept_mastery row exists (drills or checker have
            # fed it). Concepts nothing can assess yet must not block mastery.
            "has_evidence": r["score"] is not None,
        }
        for r in rows
    ]


def _resolve_items(conn, lesson_id: str) -> list[dict]:
    rows = conn.execute(
        "select * from lesson_items where lesson_id = ? order by seq", (lesson_id,)
    ).fetchall()
    items = []
    for r in rows:
        item = {"id": r["id"], "kind": r["kind"], "ref": r["ref"], "seq": r["seq"]}
        if r["kind"] == "read":
            src = conn.execute(
                "select title, body, source_is_pd from source_texts where ref = ?",
                (r["ref"],),
            ).fetchone()
            if src and src["source_is_pd"]:
                item["read"] = {"title": src["title"], "body": src["body"], "in_app": True}
            else:
                # pointer-only: non-PD sources never render in-app (by data,
                # not by language branching)
                item["read"] = {
                    "title": r["ref"],
                    "pointer": f"Read {r['ref'].replace(':', ' ch. ')} in your copy of the book",
                    "in_app": False,
                }
        elif r["kind"] == "drill" and r["ref"].startswith("deckname:"):
            deck = _deck_by_name(conn, r["ref"].split(":", 1)[1])
            if deck:
                config = json.loads(deck["config"] or "{}")
                item["deck"] = {
                    "id": deck["id"],
                    "name": deck["name"],
                    **_deck_mastery_stats(conn, deck["id"], config),
                }
            else:
                item["deck"] = None  # not built yet (build-chapter.cmd)
        return_pending = r["kind"] in ("translate", "compose") and r["ref"] == "pending"
        if return_pending:
            item["pending"] = True
        items.append(item)
    return items


def _evaluate_mastery(conn, lesson) -> bool:
    """True if the active lesson meets the mastery bar right now."""
    items = _resolve_items(conn, lesson["id"])
    deck_stats = [i["deck"] for i in items if i["kind"] == "drill"]
    if any(d is None for d in deck_stats):
        return False  # decks not built yet
    concept_scores = [
        c["score"] for c in _concept_scores(conn, lesson["chapter_ref"]) if c["has_evidence"]
    ]
    threshold = deck_stats[0]["retention_threshold"] if deck_stats else 0.9
    return mastery.lesson_mastered(
        [{"all_review": d["all_review"], "retention": d["retention"]} for d in deck_stats],
        concept_scores,
        retention_threshold=threshold,
    )


@router.get("")
def list_lessons() -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute("select * from lessons order by seq").fetchall()
        out = []
        promoted = False
        for row in rows:
            lesson = dict(row)
            if lesson["status"] == "active" and not promoted and _evaluate_mastery(conn, lesson):
                conn.execute(
                    "update lessons set status='mastered' where id = ?", (lesson["id"],)
                )
                lesson["status"] = "mastered"
                nxt = conn.execute(
                    "select id from lessons where status='locked' order by seq limit 1"
                ).fetchone()
                if nxt:
                    conn.execute("update lessons set status='active' where id = ?", (nxt["id"],))
                    promoted = True
                conn.commit()
            # live due counts keep the spiral visible on mastered lessons
            items = _resolve_items(conn, lesson["id"])
            lesson["due"] = sum(
                (i["deck"] or {}).get("due", 0) for i in items if i["kind"] == "drill"
            )
            lesson["decks_built"] = all(
                i["deck"] is not None for i in items if i["kind"] == "drill"
            )
            out.append(lesson)
        # re-read statuses in case promotion changed a row already emitted
        statuses = {r["id"]: r["status"] for r in conn.execute("select id, status from lessons")}
        for lesson in out:
            lesson["status"] = statuses.get(lesson["id"], lesson["status"])
        return out
    finally:
        conn.close()


@router.get("/{lesson_id}")
def get_lesson(lesson_id: str) -> dict:
    conn = db.get_conn()
    try:
        row = conn.execute("select * from lessons where id = ?", (lesson_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "lesson not found")
        lesson = dict(row)
        lesson["items"] = _resolve_items(conn, lesson_id)
        lesson["concepts"] = _concept_scores(conn, lesson["chapter_ref"])
        return lesson
    finally:
        conn.close()


class StatusIn(BaseModel):
    status: Literal["locked", "active", "mastered"]


@router.post("/{lesson_id}/status")
def set_status(lesson_id: str, body: StatusIn) -> dict:
    """Manual override — Jess outranks the model of her own mastery."""
    conn = db.get_conn()
    try:
        row = conn.execute("select * from lessons where id = ?", (lesson_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "lesson not found")
        conn.execute("update lessons set status = ? where id = ?", (body.status, lesson_id))
        conn.commit()
        return {"id": lesson_id, "status": body.status}
    finally:
        conn.close()
