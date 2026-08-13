"""FSRS scheduling — the only place that touches py-fsrs.

Divergence Rule 3: the drill loop never calls a model. Everything here is
SQLite + py-fsrs. The spiral method is FSRS's forgetting curve: mastered
cards resurface indefinitely at growing intervals.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fsrs import Card as FsrsCard
from fsrs import Rating, Scheduler, State

from . import db

# Default scheduler: desired retention 0.9, standard learning steps, fuzzing on.
_scheduler = Scheduler()

_STATE_TO_TEXT = {State.Learning: "learning", State.Review: "review", State.Relearning: "relearning"}
_TEXT_TO_STATE = {v: k for k, v in _STATE_TO_TEXT.items()}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _load_fsrs_card(row) -> FsrsCard:
    """Reconstruct a py-fsrs Card from a card_state row. 'new' rows become
    fresh cards due now."""
    if row["state"] == "new":
        return FsrsCard()
    return FsrsCard(
        state=_TEXT_TO_STATE.get(row["state"], State.Learning),
        step=row["step"],
        stability=row["stability"],
        difficulty=row["difficulty"],
        due=_parse_dt(row["due"]) or _now(),
        last_review=_parse_dt(row["last_review"]),
    )


def _new_introduced_today(conn, deck_id: str) -> int:
    """Cards in this deck whose first-ever review happened today (UTC)."""
    row = conn.execute(
        """
        select count(*) as n from (
          select rl.card_id, min(rl.reviewed_at) as first_review
          from review_log rl
          join cards c on c.id = rl.card_id
          where c.deck_id = ?
          group by rl.card_id
          having date(first_review) = date('now')
        )
        """,
        (deck_id,),
    ).fetchone()
    return row["n"]


def build_queue(conn, deck_id: str, limit: int = 200) -> dict:
    """Due reviews first (oldest due first), then new cards up to the deck's
    newPerDay budget for today."""
    deck = conn.execute(
        "select config from decks where id = ? and deleted_at is null", (deck_id,)
    ).fetchone()
    if deck is None:
        return {"error": "deck not found"}
    config = json.loads(deck["config"] or "{}")
    new_per_day = int(config.get("newPerDay", 10))

    due_rows = conn.execute(
        """
        select c.*, s.state as fsrs_state, s.reps, s.due
        from cards c join card_state s on s.card_id = c.id
        where c.deck_id = ? and c.deleted_at is null
          and s.state != 'new' and s.due <= datetime('now')
        order by s.due limit ?
        """,
        (deck_id, limit),
    ).fetchall()

    new_budget = max(0, new_per_day - _new_introduced_today(conn, deck_id))
    new_rows = conn.execute(
        """
        select c.*, s.state as fsrs_state, s.reps, s.due
        from cards c join card_state s on s.card_id = c.id
        where c.deck_id = ? and c.deleted_at is null and s.state = 'new'
        order by c.created_at limit ?
        """,
        (deck_id, new_budget),
    ).fetchall()

    def to_entry(row) -> dict:
        entry = {
            "id": row["id"],
            "deck_id": row["deck_id"],
            "card_type": row["card_type"],
            "payload": json.loads(row["payload"]),
            "state": row["fsrs_state"],
            "reps": row["reps"],
            "due": row["due"],
        }
        return entry

    return {
        "queue": [to_entry(r) for r in list(due_rows) + list(new_rows)],
        "counts": {
            "due": len(due_rows),
            "new": len(new_rows),
            "new_budget_left_today": new_budget,
        },
    }


def grade(conn, card_id: str, rating: int, now: datetime | None = None) -> dict:
    """Apply a 1–4 rating: update card_state + append review_log atomically
    (single connection, single commit by the caller's router)."""
    row = conn.execute(
        """
        select s.*, c.deleted_at from card_state s
        join cards c on c.id = s.card_id
        where s.card_id = ?
        """,
        (card_id,),
    ).fetchone()
    if row is None or row["deleted_at"] is not None:
        return {"error": "card not found"}

    review_time = now or _now()
    fsrs_card = _load_fsrs_card(row)
    last_review = _parse_dt(row["last_review"])
    elapsed_days = (
        (review_time - last_review).total_seconds() / 86400.0 if last_review else None
    )

    updated, _log = _scheduler.review_card(fsrs_card, Rating(rating), review_datetime=review_time)
    scheduled_days = (updated.due - review_time).total_seconds() / 86400.0

    conn.execute(
        """
        update card_state
        set stability = ?, difficulty = ?, due = ?, last_review = ?,
            reps = reps + 1, lapses = lapses + ?, state = ?, step = ?
        where card_id = ?
        """,
        (
            updated.stability,
            updated.difficulty,
            updated.due.isoformat(),
            review_time.isoformat(),
            1 if (rating == int(Rating.Again) and row["state"] in ("review", "relearning")) else 0,
            _STATE_TO_TEXT[updated.state],
            updated.step,
            card_id,
        ),
    )
    conn.execute(
        """
        insert into review_log (id, card_id, rating, reviewed_at, elapsed_days, scheduled_days)
        values (?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), card_id, rating, review_time.isoformat(), elapsed_days, scheduled_days),
    )
    return {
        "card_id": card_id,
        "state": _STATE_TO_TEXT[updated.state],
        "due": updated.due.isoformat(),
        "scheduled_days": scheduled_days,
    }


def deck_stats(conn, deck_id: str) -> dict:
    """Due today / new remaining / retention estimate for a deck."""
    due = conn.execute(
        """
        select count(*) as n from cards c join card_state s on s.card_id = c.id
        where c.deck_id = ? and c.deleted_at is null
          and s.state != 'new' and s.due <= datetime('now')
        """,
        (deck_id,),
    ).fetchone()["n"]
    new = conn.execute(
        """
        select count(*) as n from cards c join card_state s on s.card_id = c.id
        where c.deck_id = ? and c.deleted_at is null and s.state = 'new'
        """,
        (deck_id,),
    ).fetchone()["n"]

    review_rows = conn.execute(
        """
        select s.* from cards c join card_state s on s.card_id = c.id
        where c.deck_id = ? and c.deleted_at is null and s.state = 'review'
        """,
        (deck_id,),
    ).fetchall()
    retention = None
    if review_rows:
        values = [_scheduler.get_card_retrievability(_load_fsrs_card(r)) for r in review_rows]
        retention = sum(values) / len(values)

    return {"due": due, "new": new, "retention": retention}
