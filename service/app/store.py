"""Query functions for decks and cards — all SQL lives here, not in routes."""

from __future__ import annotations

import json
import uuid
from typing import Any

from . import db


def make_id() -> str:
    return str(uuid.uuid4())


def _touch(conn, table: str, row_id: str) -> None:
    conn.execute(
        f"update {table} set updated_at = datetime('now') where id = ?", (row_id,)
    )


# ---- decks ----------------------------------------------------------------

def deck_row_to_dict(row) -> dict:
    d = dict(row)
    d["config"] = json.loads(d.get("config") or "{}")
    return d


def list_decks(conn) -> list[dict]:
    rows = conn.execute(
        """
        select d.*, count(c.id) as card_count
        from decks d
        left join cards c on c.deck_id = d.id and c.deleted_at is null
        where d.deleted_at is null
        group by d.id
        order by d.created_at
        """
    ).fetchall()
    return [deck_row_to_dict(r) for r in rows]


def get_deck(conn, deck_id: str) -> dict | None:
    row = conn.execute(
        "select * from decks where id = ? and deleted_at is null", (deck_id,)
    ).fetchone()
    return deck_row_to_dict(row) if row else None


def create_deck(conn, name: str, topic: str, config: dict) -> str:
    deck_id = make_id()
    conn.execute(
        "insert into decks (id, name, topic, config) values (?, ?, ?, ?)",
        (deck_id, db.nfc(name), db.nfc(topic), json.dumps(config)),
    )
    return deck_id


def update_deck(conn, deck_id: str, fields: dict[str, Any]) -> None:
    if "name" in fields:
        conn.execute("update decks set name = ? where id = ?", (db.nfc(fields["name"]), deck_id))
    if "topic" in fields:
        conn.execute("update decks set topic = ? where id = ?", (db.nfc(fields["topic"]), deck_id))
    if "config" in fields:
        conn.execute("update decks set config = ? where id = ?", (json.dumps(fields["config"]), deck_id))
    _touch(conn, "decks", deck_id)


def soft_delete_deck(conn, deck_id: str) -> None:
    conn.execute("update decks set deleted_at = datetime('now') where id = ?", (deck_id,))


# ---- cards ----------------------------------------------------------------

def card_row_to_dict(row) -> dict:
    c = dict(row)
    c["payload"] = json.loads(c["payload"])
    c["source"] = json.loads(c["source"]) if c.get("source") else None
    return c


def list_cards(conn, deck_id: str) -> list[dict]:
    rows = conn.execute(
        "select * from cards where deck_id = ? and deleted_at is null order by created_at",
        (deck_id,),
    ).fetchall()
    return [card_row_to_dict(r) for r in rows]


def get_card(conn, card_id: str) -> dict | None:
    row = conn.execute(
        "select * from cards where id = ? and deleted_at is null", (card_id,)
    ).fetchone()
    return card_row_to_dict(row) if row else None


def create_card(
    conn, deck_id: str, card_type: str, payload: dict, source: dict | None = None
) -> str:
    card_id = make_id()
    conn.execute(
        "insert into cards (id, deck_id, card_type, payload, source) values (?, ?, ?, ?, ?)",
        (
            card_id,
            deck_id,
            card_type,
            db.nfc(json.dumps(payload, ensure_ascii=False)),
            json.dumps(source, ensure_ascii=False) if source else None,
        ),
    )
    # every card gets FSRS state immediately: new, due now
    conn.execute(
        "insert into card_state (card_id, due) values (?, datetime('now'))",
        (card_id,),
    )
    return card_id


def update_card_payload(conn, card_id: str, payload: dict) -> None:
    conn.execute(
        "update cards set payload = ? where id = ?",
        (db.nfc(json.dumps(payload, ensure_ascii=False)), card_id),
    )
    _touch(conn, "cards", card_id)


def soft_delete_card(conn, card_id: str) -> None:
    conn.execute("update cards set deleted_at = datetime('now') where id = ?", (card_id,))
