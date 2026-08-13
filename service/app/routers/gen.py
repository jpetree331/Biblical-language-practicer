"""Admin endpoints for the generation pipeline. Synchronous by design —
single local user; a batch takes a minute or two and the response carries the
full ledger entry."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..gen import pipeline

router = APIRouter(prefix="/api/gen", tags=["generation"])


class BatchIn(BaseModel):
    spec: dict[str, Any]


@router.post("/run")
async def run(body: BatchIn) -> dict:
    try:
        return await pipeline.run_batch(body.spec)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(422, str(e))


@router.get("/batches")
def batches() -> list[dict]:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "select * from gen_batches order by started_at desc limit 100"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
