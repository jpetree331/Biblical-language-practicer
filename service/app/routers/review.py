"""Review endpoints — thin wrappers over scheduler.py (Divergence Rule 3:
served and graded entirely from SQLite + FSRS; no model calls)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db, scheduler

router = APIRouter(prefix="/api/review", tags=["review"])


class GradeIn(BaseModel):
    card_id: str
    rating: int = Field(ge=1, le=4)


@router.get("/queue")
def queue(deck_id: str, limit: int = 200) -> dict:
    conn = db.get_conn()
    try:
        result = scheduler.build_queue(conn, deck_id, limit)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    finally:
        conn.close()


@router.post("/grade")
def grade(body: GradeIn) -> dict:
    conn = db.get_conn()
    try:
        result = scheduler.grade(conn, body.card_id, body.rating)
        if "error" in result:
            raise HTTPException(404, result["error"])
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/stats")
def stats(deck_id: str) -> dict:
    conn = db.get_conn()
    try:
        return scheduler.deck_stats(conn, deck_id)
    finally:
        conn.close()
