"""Deck CRUD routes. SQL lives in store.py; routes stay thin."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db, store

router = APIRouter(prefix="/api/decks", tags=["decks"])


class DeckIn(BaseModel):
    name: str
    topic: str = "general"
    config: dict[str, Any] = {}


class DeckPatch(BaseModel):
    name: str | None = None
    topic: str | None = None
    config: dict[str, Any] | None = None


@router.get("")
def list_decks() -> list[dict]:
    conn = db.get_conn()
    try:
        return store.list_decks(conn)
    finally:
        conn.close()


@router.post("", status_code=201)
def create_deck(body: DeckIn) -> dict:
    conn = db.get_conn()
    try:
        deck_id = store.create_deck(conn, body.name, body.topic, body.config)
        conn.commit()
        return store.get_deck(conn, deck_id)
    finally:
        conn.close()


@router.get("/{deck_id}")
def get_deck(deck_id: str) -> dict:
    conn = db.get_conn()
    try:
        deck = store.get_deck(conn, deck_id)
        if deck is None:
            raise HTTPException(404, "deck not found")
        return deck
    finally:
        conn.close()


@router.patch("/{deck_id}")
def patch_deck(deck_id: str, body: DeckPatch) -> dict:
    conn = db.get_conn()
    try:
        if store.get_deck(conn, deck_id) is None:
            raise HTTPException(404, "deck not found")
        store.update_deck(conn, deck_id, body.model_dump(exclude_none=True))
        conn.commit()
        return store.get_deck(conn, deck_id)
    finally:
        conn.close()


@router.delete("/{deck_id}", status_code=204)
def delete_deck(deck_id: str) -> None:
    conn = db.get_conn()
    try:
        if store.get_deck(conn, deck_id) is None:
            raise HTTPException(404, "deck not found")
        store.soft_delete_deck(conn, deck_id)
        conn.commit()
    finally:
        conn.close()


@router.get("/{deck_id}/cards")
def list_cards(deck_id: str) -> list[dict]:
    conn = db.get_conn()
    try:
        if store.get_deck(conn, deck_id) is None:
            raise HTTPException(404, "deck not found")
        return store.list_cards(conn, deck_id)
    finally:
        conn.close()
