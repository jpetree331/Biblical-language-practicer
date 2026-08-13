"""Card CRUD routes. Payloads are validated against the card-type registry
on every write (Divergence Rule 1 — no per-type branching, just the registry)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import card_types, db, store

router = APIRouter(prefix="/api/cards", tags=["cards"])


class CardIn(BaseModel):
    deck_id: str
    card_type: str
    payload: dict[str, Any]
    source: dict[str, Any] | None = None


class CardPatch(BaseModel):
    payload: dict[str, Any]


def _validate_or_422(card_type: str, payload: dict) -> None:
    problems = card_types.validate_payload(card_type, payload)
    if problems:
        raise HTTPException(422, {"payload_errors": problems})


@router.post("", status_code=201)
def create_card(body: CardIn) -> dict:
    _validate_or_422(body.card_type, body.payload)
    conn = db.get_conn()
    try:
        if store.get_deck(conn, body.deck_id) is None:
            raise HTTPException(404, "deck not found")
        card_id = store.create_card(conn, body.deck_id, body.card_type, body.payload, body.source)
        conn.commit()
        return store.get_card(conn, card_id)
    finally:
        conn.close()


@router.patch("/{card_id}")
def patch_card(card_id: str, body: CardPatch) -> dict:
    conn = db.get_conn()
    try:
        card = store.get_card(conn, card_id)
        if card is None:
            raise HTTPException(404, "card not found")
        _validate_or_422(card["card_type"], body.payload)
        store.update_card_payload(conn, card_id, body.payload)
        conn.commit()
        return store.get_card(conn, card_id)
    finally:
        conn.close()


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str) -> None:
    conn = db.get_conn()
    try:
        if store.get_card(conn, card_id) is None:
            raise HTTPException(404, "card not found")
        store.soft_delete_card(conn, card_id)
        conn.commit()
    finally:
        conn.close()
