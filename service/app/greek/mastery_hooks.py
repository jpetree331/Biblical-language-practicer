"""Greek-specific review hooks (Divergence Rule 6: Greek logic lives here and
in registry entries — the deck/review core stays topic-agnostic; it only knows
'this card type has an on_review hook').

A parsing-card review feeds the concept it drills: parse code → GK concept id
→ concept_mastery update (decay-then-delta, both from the shared mastery
model). Only concepts the syllabus map created are updated — junk parse codes
can't invent curriculum."""

from __future__ import annotations

from datetime import datetime, timezone

from .. import mastery

# MorphGNT parse-code letters → concept-id fragments
_TENSE = {"P": "PRES", "I": "IMPF", "F": "FUT", "A": "AOR", "X": "PERF", "Y": "PLUP"}
_VOICE = {"A": "ACT", "M": "MID", "P": "PASS"}
_MOOD = {"I": "IND", "S": "SUBJ", "D": "IMPV", "N": "INF", "P": "PTCP"}


def parse_to_concept_id(parse: str) -> str | None:
    """'V- 3PAI-S--' → 'GK.PRES.ACT.IND' (verbs only)."""
    parts = parse.split()
    if len(parts) != 2 or parts[0] != "V-" or len(parts[1]) != 8:
        return None
    code = parts[1]
    tense, voice, mood = _TENSE.get(code[1]), _VOICE.get(code[2]), _MOOD.get(code[3])
    if not (tense and voice and mood):
        return None
    return f"GK.{tense}.{voice}.{mood}"


def _days_since(iso: str | None) -> float:
    if not iso:
        return 0.0
    then = datetime.fromisoformat(iso)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - then).total_seconds() / 86400.0)


def on_parsing_review(conn, payload: dict, rating: int) -> None:
    """Registry hook: called by the scheduler after any 'parsing' card grade."""
    concept_id = parse_to_concept_id(str(payload.get("parse", "")))
    if concept_id is None:
        return
    exists = conn.execute("select 1 from concepts where id = ?", (concept_id,)).fetchone()
    if not exists:
        return  # not part of the loaded curriculum
    row = conn.execute(
        "select score, updated_at from concept_mastery where concept_id = ?", (concept_id,)
    ).fetchone()
    if row is None:
        new_score = mastery.apply_review(0.0, rating)
        conn.execute(
            "insert into concept_mastery (concept_id, score) values (?, ?)",
            (concept_id, new_score),
        )
    else:
        decayed = mastery.apply_decay(row["score"], _days_since(row["updated_at"]))
        new_score = mastery.apply_review(decayed, rating)
        conn.execute(
            "update concept_mastery set score = ?, updated_at = datetime('now') where concept_id = ?",
            (new_score, concept_id),
        )
