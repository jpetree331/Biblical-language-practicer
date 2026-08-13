"""Exercise endpoints: fetch, submit (→ checker), list by lesson."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..greek import checker

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("/by-lesson/{lesson_id}")
def by_lesson(lesson_id: str) -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "select id, kind, created_at from exercises where lesson_id = ? order by created_at",
            (lesson_id,),
        ).fetchall()
        out = []
        for r in rows:
            latest = conn.execute(
                "select score, submitted_at from submissions where exercise_id = ? "
                "order by submitted_at desc limit 1",
                (r["id"],),
            ).fetchone()
            out.append(
                {
                    "id": r["id"],
                    "kind": r["kind"],
                    "last_score": latest["score"] if latest else None,
                    "attempted": latest is not None,
                }
            )
        return out
    finally:
        conn.close()


@router.get("/{exercise_id}")
def get_exercise(exercise_id: str) -> dict:
    conn = db.get_conn()
    try:
        row = conn.execute("select * from exercises where id = ?", (exercise_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "exercise not found")
        prompt = json.loads(row["prompt"])
        # the answer key is never sent to the client before submission
        return {"id": row["id"], "kind": row["kind"], "lesson_id": row["lesson_id"], "prompt": prompt}
    finally:
        conn.close()


class SubmitIn(BaseModel):
    answer: str


@router.post("/{exercise_id}/submit")
async def submit(exercise_id: str, body: SubmitIn) -> dict:
    if not body.answer.strip():
        raise HTTPException(422, "answer is empty")
    result = await checker.check_submission(exercise_id, body.answer.strip())
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
