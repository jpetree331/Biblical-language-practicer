"""Deck export/import. JSON is the canonical format and carries FSRS state;
CSV (basic cards only) is handled client-side and arrives here as canonical
JSON. Import is parse-then-confirm: preview mode reports what would be
created; commit mode creates it."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import card_types, db, store

router = APIRouter(tags=["transfer"])

FORMAT = "scriptorium-deck@1"

STATE_FIELDS = ("stability", "difficulty", "due", "last_review", "reps", "lapses", "state", "step")


@router.get("/api/decks/{deck_id}/export")
def export_deck(deck_id: str) -> dict:
    conn = db.get_conn()
    try:
        deck = store.get_deck(conn, deck_id)
        if deck is None:
            raise HTTPException(404, "deck not found")
        cards = store.list_cards(conn, deck_id)
        out_cards = []
        for card in cards:
            state_row = conn.execute(
                "select * from card_state where card_id = ?", (card["id"],)
            ).fetchone()
            out_cards.append(
                {
                    "card_type": card["card_type"],
                    "payload": card["payload"],
                    "source": card["source"],
                    "state": {k: state_row[k] for k in STATE_FIELDS} if state_row else None,
                }
            )
        return {
            "format": FORMAT,
            "deck": {"name": deck["name"], "topic": deck["topic"], "config": deck["config"]},
            "cards": out_cards,
        }
    finally:
        conn.close()


class ImportIn(BaseModel):
    data: dict[str, Any]
    mode: Literal["preview", "commit"]


def _inspect(data: dict) -> tuple[dict, list[dict], list[str]]:
    """Validate an import document. Returns (deck_info, good_cards, warnings)."""
    warnings: list[str] = []
    if data.get("format") != FORMAT:
        raise HTTPException(422, f"unknown format — expected '{FORMAT}'")
    deck = data.get("deck") or {}
    if not isinstance(deck.get("name"), str) or not deck["name"].strip():
        raise HTTPException(422, "deck.name is required")
    cards = data.get("cards")
    if not isinstance(cards, list):
        raise HTTPException(422, "cards must be a list")

    good: list[dict] = []
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            warnings.append(f"card {i + 1} skipped: not an object")
            continue
        ctype = card.get("card_type")
        payload = card.get("payload")
        problems = card_types.validate_payload(str(ctype), payload)
        if problems:
            warnings.append(f"card {i + 1} ({ctype}) skipped: {'; '.join(problems)}")
            continue
        good.append(card)
    return deck, good, warnings


@router.post("/api/import")
def import_deck(body: ImportIn) -> dict:
    deck, good, warnings = _inspect(body.data)
    counts: dict[str, int] = {}
    with_state = 0
    for card in good:
        counts[card["card_type"]] = counts.get(card["card_type"], 0) + 1
        if card.get("state"):
            with_state += 1

    preview = {
        "deck_name": deck["name"].strip(),
        "topic": deck.get("topic") or "general",
        "counts": counts,
        "total": len(good),
        "with_fsrs_state": with_state,
        "warnings": warnings,
    }
    if body.mode == "preview":
        return preview

    conn = db.get_conn()
    try:
        deck_id = store.create_deck(
            conn,
            deck["name"].strip(),
            deck.get("topic") or "general",
            deck.get("config") if isinstance(deck.get("config"), dict) else {},
        )
        for card in good:
            card_id = store.create_card(
                conn, deck_id, card["card_type"], card["payload"], card.get("source")
            )
            state = card.get("state")
            if isinstance(state, dict) and state.get("state"):
                conn.execute(
                    """
                    update card_state
                    set stability=?, difficulty=?, due=coalesce(?, due), last_review=?,
                        reps=?, lapses=?, state=?, step=?
                    where card_id=?
                    """,
                    (
                        state.get("stability"),
                        state.get("difficulty"),
                        state.get("due"),
                        state.get("last_review"),
                        int(state.get("reps") or 0),
                        int(state.get("lapses") or 0),
                        str(state.get("state")),
                        state.get("step"),
                        card_id,
                    ),
                )
        conn.commit()
        return {**preview, "deck_id": deck_id}
    finally:
        conn.close()
