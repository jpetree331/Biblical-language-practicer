"""The checker — the highest-stakes AI surface in the app. Jess is a beginner
and cannot always spot a wrong correction, so Divergence Rule 4 is enforced
here at full strength:

- The checker's feedback is STRUCTURED and every note cites a token id.
- Programmatic validation before display: a note whose token id is not in the
  passage, or whose claimed parse disagrees with the stored parse code, is
  WITHHELD — dropped from display, logged to docs/generation/rejects/checker/,
  and counted, so the UI can say "N notes were withheld (failed verification)".
  Silence is visible, never silent.
- Every surviving note is footnoted "checked against MorphGNT <ref>" by the UI.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from .. import db, mastery
from ..gen import ai
from . import mastery_hooks

REJECTS_DIR = db.REPO_ROOT / "docs" / "generation" / "rejects" / "checker"

CHECK_SYSTEM = """You are a patient, precise Koine Greek instructor checking a
beginner's translation. You receive the passage's full token rows
(surface/lemma/parse/gloss — the ONLY source of truth about the Greek), a
reference answer key, and the student's submission.

Judge the SUBSTANCE of their rendering, not its phrasing. A different but
faithful rendering is correct.

Output ONE strict JSON object, nothing else:
{"score": <0.0-1.0 overall faithfulness>,
 "summary": "<one encouraging, honest sentence>",
 "notes": [
   {"token_id": <id of the token this note concerns — REQUIRED, from the rows>,
    "kind": "error" | "nitpick" | "praise",
    "claimed_parse": "<the token's parse code EXACTLY as given in its row>",
    "note": "<one line: what went wrong/right and why>"}
 ]}
Rules: cite only token ids from the supplied rows; copy claimed_parse verbatim
from the row you are citing; tag real mistranslations as "error", stylistic
points as "nitpick". No notes is fine for a clean translation.

For composition exercises (student wrote GREEK from an English prompt): the
answer key is the attested NT sentence. Valid alternatives are acceptable —
distinguish "wrong" from "different but grammatically sound"; mark the latter
"nitpick" with a note pointing to the attested pattern."""


def _validate_notes(conn, notes: Any, passage_token_ids: set[int]) -> tuple[list[dict], list[dict]]:
    """Split checker notes into (displayable, withheld-with-reasons)."""
    good: list[dict] = []
    withheld: list[dict] = []
    if not isinstance(notes, list):
        return good, [{"note": notes, "reason": "notes was not a list"}]
    for note in notes:
        if not isinstance(note, dict):
            withheld.append({"note": note, "reason": "not an object"})
            continue
        tid = note.get("token_id")
        if tid not in passage_token_ids:
            withheld.append({"note": note, "reason": f"token id {tid!r} is not in this passage"})
            continue
        row = conn.execute(
            "select book, chapter, verse, parse, surface from corpus_tokens where id = ?", (tid,)
        ).fetchone()
        claimed = note.get("claimed_parse")
        if claimed and claimed != row["parse"]:
            withheld.append(
                {
                    "note": note,
                    "reason": f"claimed parse {claimed!r} != stored {row['parse']!r} (stored code is authoritative)",
                }
            )
            continue
        if note.get("kind") not in ("error", "nitpick", "praise"):
            withheld.append({"note": note, "reason": f"bad kind {note.get('kind')!r}"})
            continue
        good.append(
            {
                "token_id": tid,
                "kind": note["kind"],
                "note": str(note.get("note", "")),
                "surface": row["surface"],
                "checked_against": f"MorphGNT {row['book']}.{row['chapter']}.{row['verse']}",
            }
        )
    return good, withheld


def _update_concepts(conn, tokens: list[dict], error_token_ids: set[int]) -> list[str]:
    """Checker results feed concept mastery: each verb token in the passage
    scores its concept — rating 1 if an error note tagged it, else 3."""
    touched = []
    for t in tokens:
        concept_id = mastery_hooks.parse_to_concept_id(t["parse"])
        if concept_id is None:
            continue
        if not conn.execute("select 1 from concepts where id = ?", (concept_id,)).fetchone():
            continue
        rating = 1 if t["id"] in error_token_ids else 3
        row = conn.execute(
            "select score, updated_at from concept_mastery where concept_id = ?", (concept_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "insert into concept_mastery (concept_id, score) values (?, ?)",
                (concept_id, mastery.apply_review(0.0, rating)),
            )
        else:
            decayed = mastery.apply_decay(row["score"], mastery_hooks._days_since(row["updated_at"]))
            conn.execute(
                "update concept_mastery set score = ?, updated_at = datetime('now') where concept_id = ?",
                (mastery.apply_review(decayed, rating), concept_id),
            )
        touched.append(concept_id)
    return touched


async def check_submission(exercise_id: str, answer: str) -> dict:
    ai.assert_subscription_auth()
    conn = db.get_conn()
    try:
        ex = conn.execute("select * from exercises where id = ?", (exercise_id,)).fetchone()
        if ex is None:
            return {"error": "exercise not found"}
        prompt_doc = json.loads(ex["prompt"])
        answer_key = json.loads(ex["answer_key"] or "{}")

        # token rows: translate exercises carry them in prompt; compose in key
        tokens = prompt_doc.get("tokens") or answer_key.get("tokens") or []
        token_ids = {t["id"] for t in tokens}

        model_input = {
            "exercise_kind": ex["kind"],
            "passage_tokens": tokens,
            "answer_key": answer_key,
            "student_submission": answer,
        }
        raw, _ = await ai.ask(
            ai.VERIFIER_MODEL, CHECK_SYSTEM, json.dumps(model_input, ensure_ascii=False)
        )
        try:
            result = ai.extract_json(raw)
        except ValueError:
            result = {"score": None, "summary": "", "notes": []}

        notes, withheld = _validate_notes(conn, result.get("notes", []), token_ids)
        if withheld:
            REJECTS_DIR.mkdir(parents=True, exist_ok=True)
            (REJECTS_DIR / f"{exercise_id[:8]}-{uuid.uuid4().hex[:6]}.json").write_text(
                json.dumps({"exercise_id": exercise_id, "withheld": withheld}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        score = result.get("score")
        score = float(score) if isinstance(score, (int, float)) else None
        error_ids = {n["token_id"] for n in notes if n["kind"] == "error"}
        touched = _update_concepts(conn, tokens, error_ids)

        feedback = {
            "score": score,
            "summary": str(result.get("summary", "")),
            "notes": notes,
            "withheld_count": len(withheld),
        }
        submission_id = str(uuid.uuid4())
        conn.execute(
            "insert into submissions (id, exercise_id, answer, feedback, score) values (?, ?, ?, ?, ?)",
            (submission_id, exercise_id, db.nfc(answer), json.dumps(feedback, ensure_ascii=False), score),
        )
        conn.commit()
        return {"submission_id": submission_id, **feedback, "concepts_updated": touched}
    finally:
        conn.close()
