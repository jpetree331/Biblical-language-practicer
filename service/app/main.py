"""Scriptorium FastAPI service — port 8012, local only."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from . import db
from .routers import cards, corpus, decks, review, transfer

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.bootstrap()
    yield


app = FastAPI(title="Scriptorium", version=VERSION, lifespan=lifespan)
app.include_router(decks.router)
app.include_router(cards.router)
app.include_router(review.router)
app.include_router(transfer.router)
app.include_router(corpus.router)


@app.get("/api/health")
def health() -> dict:
    try:
        conn = db.get_conn()
        try:
            conn.execute("select 1").fetchone()
        finally:
            conn.close()
        db_ok = True
    except sqlite3.Error:
        db_ok = False
    return {"ok": db_ok, "db": str(db.DB_PATH), "version": VERSION}


class EchoIn(BaseModel):
    text: str


@app.post("/api/dev/roundtrip")
def roundtrip(body: EchoIn) -> dict:
    """Scratch endpoint for the Sprint 0 Unicode VERIFY: store the given text
    in SQLite, read it back, return both the stored value and a byte-equality
    flag against the NFC-normalized input. Kept because it is a cheap
    permanent canary for encoding regressions."""
    normalized = db.nfc(body.text)
    conn = db.get_conn()
    try:
        conn.execute(
            "create table if not exists _roundtrip (id integer primary key, text text not null)"
        )
        cur = conn.execute("insert into _roundtrip (text) values (?)", (normalized,))
        row_id = cur.lastrowid
        conn.commit()
        row = conn.execute("select text from _roundtrip where id = ?", (row_id,)).fetchone()
    finally:
        conn.close()
    stored = row["text"]
    return {
        "sent": body.text,
        "stored": stored,
        "nfc_byte_identical": stored.encode("utf-8") == normalized.encode("utf-8"),
    }
