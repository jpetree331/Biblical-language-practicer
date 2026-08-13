"""Generation pipeline: Generate → Validate (programmatic) → Verify (second
model) → Land.

Divergence Rule 4, load-bearing: nothing lands without passing programmatic
citation validation, and every failure is written to
docs/generation/rejects/<batch>/ with its reason — never silently dropped.

Grounding architecture: the model never supplies corpus facts. SQL selects the
actual rows (lemmas, surfaces, parse codes, refs, token ids); the model
arranges and glosses them. Payload fields that mirror the corpus
(surface/lemma/parse/ref) are built from the DB rows the model cites, then
validated against the DB again before landing (belt and braces — this also
catches invented token ids).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .. import card_types, db, store
from . import ai

REJECTS_DIR = db.REPO_ROOT / "docs" / "generation" / "rejects"

VOCAB_SYSTEM = """You are a Koine Greek vocabulary editor for a beginner's
spaced-repetition deck. You will receive corpus rows (lemma, frequency rank,
occurrence count, and sample occurrences with token ids). For EACH lemma
produce one card object:
  {"lemma": "<exactly as given>",
   "gloss": "<concise classroom-standard English gloss, 1-5 words>",
   "example_token_ids": [<1 or 2 token ids chosen from that lemma's samples>]}
Rules: never invent token ids; only use ids listed for that lemma. Keep
glosses conventional (Mounce/BDAG-style leading senses). Output a strict JSON
array of card objects, nothing else."""

PARSING_SYSTEM = """You are a Koine Greek morphology drill editor. You will
receive corpus tokens (token id, reference, surface form, lemma, parse code)
that all match a target construction. Select the best drill instances —
skip near-duplicate surface forms so the drill stays varied; prefer
pedagogically clear examples. For each selected token output:
  {"token_id": <id>, "gloss": "<English rendering of this word in its verse,
   1-4 words>"}
Select at most the requested number. Never invent token ids. Output a strict
JSON array, nothing else."""

VERIFY_SYSTEM = """You are a skeptical reviewer of generated Koine Greek
flashcards, checking against the corpus rows provided (the only source of
truth). For each candidate card judge:
- gloss accuracy (is this a correct, standard rendering?),
- data fidelity (does everything match the corpus rows?),
- pedagogical sanity (is this a reasonable beginner card?).
Output a strict JSON array, one verdict per candidate, in the same order:
  {"index": <candidate index>, "pass": true/false, "reason": "<one line>"}
Fail anything dubious — a wrong card that lands teaches an error."""


# ---- corpus selection (SQL, no model) --------------------------------------

def select_vocab_rows(conn, rank_from: int, rank_to: int) -> list[dict]:
    lemmas = conn.execute(
        """
        select lemma, rank, count from lemma_freq
        where corpus_id = 'sblgnt' and rank between ? and ?
        order by rank, lemma
        """,
        (rank_from, rank_to),
    ).fetchall()
    rows = []
    for lem in lemmas:
        samples = conn.execute(
            """
            select id, book, chapter, verse, surface, parse from corpus_tokens
            where corpus_id = 'sblgnt' and lemma = ?
            order by id limit 3
            """,
            (lem["lemma"],),
        ).fetchall()
        rows.append(
            {
                "lemma": lem["lemma"],
                "rank": lem["rank"],
                "count": lem["count"],
                "samples": [
                    {
                        "token_id": s["id"],
                        "ref": f"{s['book']}.{s['chapter']}.{s['verse']}",
                        "surface": s["surface"],
                        "parse": s["parse"],
                    }
                    for s in samples
                ],
            }
        )
    return rows


def select_vocab_rows_by_lemmas(conn, lemmas: list[str]) -> list[dict]:
    """Like select_vocab_rows but for an explicit lemma list (chapter decks)."""
    rows = []
    for lemma in lemmas:
        lemma = db.nfc(lemma)
        freq = conn.execute(
            "select rank, count from lemma_freq where corpus_id='sblgnt' and lemma=?",
            (lemma,),
        ).fetchone()
        if freq is None:
            continue  # loader guarantees this can't happen for loaded maps
        samples = conn.execute(
            """
            select id, book, chapter, verse, surface, parse from corpus_tokens
            where corpus_id = 'sblgnt' and lemma = ? order by id limit 3
            """,
            (lemma,),
        ).fetchall()
        rows.append(
            {
                "lemma": lemma,
                "rank": freq["rank"],
                "count": freq["count"],
                "samples": [
                    {
                        "token_id": s["id"],
                        "ref": f"{s['book']}.{s['chapter']}.{s['verse']}",
                        "surface": s["surface"],
                        "parse": s["parse"],
                    }
                    for s in samples
                ],
            }
        )
    return rows


def select_parsing_rows_filtered(
    conn, parse_like: str, lemma_in: list[str], limit: int = 80
) -> list[dict]:
    """Corpus-wide tokens matching a construction, restricted to known lemmas
    (chapter parsing decks: practice new grammar on vocabulary already met)."""
    lemmas = [db.nfc(x) for x in lemma_in]
    placeholders = ",".join("?" * len(lemmas))
    tokens = conn.execute(
        f"""
        select id, book, chapter, verse, surface, lemma, parse from corpus_tokens
        where corpus_id = 'sblgnt' and parse like ? and lemma in ({placeholders})
        order by id limit ?
        """,
        (parse_like, *lemmas, limit),
    ).fetchall()
    return [
        {
            "token_id": t["id"],
            "ref": f"{t['book']}.{t['chapter']}.{t['verse']}",
            "surface": t["surface"],
            "lemma": t["lemma"],
            "parse": t["parse"],
        }
        for t in tokens
    ]


def select_parsing_rows(conn, book: str, chapter: int, parse_like: str, limit: int = 60) -> list[dict]:
    tokens = conn.execute(
        """
        select id, book, chapter, verse, surface, lemma, parse from corpus_tokens
        where corpus_id = 'sblgnt' and book = ? and chapter = ? and parse like ?
        order by id limit ?
        """,
        (book, chapter, parse_like, limit),
    ).fetchall()
    return [
        {
            "token_id": t["id"],
            "ref": f"{t['book']}.{t['chapter']}.{t['verse']}",
            "surface": t["surface"],
            "lemma": t["lemma"],
            "parse": t["parse"],
        }
        for t in tokens
    ]


# ---- candidate construction ------------------------------------------------

def _token_by_id(conn, token_id: Any) -> dict | None:
    if not isinstance(token_id, int):
        return None
    row = conn.execute(
        "select * from corpus_tokens where id = ? and corpus_id = 'sblgnt'", (token_id,)
    ).fetchone()
    return dict(row) if row else None


def build_vocab_candidates(conn, model_cards: list, corpus_rows: list[dict]) -> list[dict]:
    """Model output → full card candidates (payload + citations)."""
    by_lemma = {r["lemma"]: r for r in corpus_rows}
    candidates = []
    for item in model_cards:
        lemma = item.get("lemma") if isinstance(item, dict) else None
        row = by_lemma.get(lemma)
        examples = []
        for tid in (item.get("example_token_ids") or []) if isinstance(item, dict) else []:
            tok = _token_by_id(conn, tid)
            if tok is None:
                examples.append({"token_id": tid, "ref": "INVALID", "surface": ""})
            else:
                examples.append(
                    {
                        "token_id": tid,
                        "ref": f"{tok['book']}.{tok['chapter']}.{tok['verse']}",
                        "surface": tok["surface"],
                    }
                )
        candidates.append(
            {
                "card_type": "vocab_gk",
                "payload": {
                    "lemma": lemma or "",
                    "gloss": (item.get("gloss") or "").strip() if isinstance(item, dict) else "",
                    "rank": row["rank"] if row else -1,
                    "examples": examples,
                },
                "citations": [e["token_id"] for e in examples],
            }
        )
    return candidates


def build_parsing_candidates(conn, model_cards: list) -> list[dict]:
    candidates = []
    for item in model_cards:
        tid = item.get("token_id") if isinstance(item, dict) else None
        tok = _token_by_id(conn, tid)
        payload = {
            "surface": tok["surface"] if tok else "",
            "ref": f"{tok['book']}.{tok['chapter']}.{tok['verse']}" if tok else "INVALID",
            "lemma": tok["lemma"] if tok else "",
            "parse": tok["parse"] if tok else "",
            "gloss": (item.get("gloss") or "").strip() if isinstance(item, dict) else "",
        }
        candidates.append(
            {"card_type": "parsing", "payload": payload, "citations": [tid]}
        )
    return candidates


# ---- programmatic validation (no model) ------------------------------------

def validate_candidate(conn, cand: dict) -> str | None:
    """Return a failure reason, or None if the candidate is sound."""
    payload = cand["payload"]
    problems = card_types.validate_payload(cand["card_type"], payload)
    if problems:
        return "schema: " + "; ".join(problems)
    if not cand["citations"]:
        return "no citations"
    for tid in cand["citations"]:
        tok = _token_by_id(conn, tid)
        if tok is None:
            return f"citation {tid} does not resolve to a corpus token"
        if cand["card_type"] == "vocab_gk":
            if tok["lemma"] != payload["lemma"]:
                return (
                    f"citation {tid} lemma mismatch: token has {tok['lemma']!r}, "
                    f"card claims {payload['lemma']!r}"
                )
        if cand["card_type"] == "parsing":
            if payload["parse"] != tok["parse"]:
                return (
                    f"parse mismatch: card {payload['parse']!r} vs "
                    f"token {tok['parse']!r} (stored code is authoritative)"
                )
            if payload["surface"] != tok["surface"]:
                return f"surface mismatch: {payload['surface']!r} vs {tok['surface']!r}"
            ref = f"{tok['book']}.{tok['chapter']}.{tok['verse']}"
            if payload["ref"] != ref:
                return f"ref mismatch: {payload['ref']!r} vs {ref!r}"
    if cand["card_type"] == "vocab_gk":
        for ex in payload["examples"]:
            tok = _token_by_id(conn, ex.get("token_id"))
            if tok is None or ex.get("surface") != tok["surface"]:
                return f"example token {ex.get('token_id')} surface mismatch"
    if not payload.get("gloss"):
        return "empty gloss"
    return None


def write_reject(batch_id: str, index: int, candidate: dict, reason: str, stage: str) -> None:
    folder = REJECTS_DIR / batch_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stage}-{index:03d}.json").write_text(
        json.dumps(
            {"stage": stage, "reason": reason, "candidate": candidate},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ---- the pipeline ----------------------------------------------------------

async def run_batch(spec: dict) -> dict:
    """spec: {"kind": "vocab", "rank_from": 1, "rank_to": 40, "deck": "..."}
       or   {"kind": "parsing", "book": "John", "chapter": 1,
             "parse_like": "V- _PAI%", "max_cards": 25, "deck": "..."}"""
    ai.assert_subscription_auth()
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    conn = db.get_conn()
    try:
        conn.execute(
            "insert into gen_batches (id, spec, models) values (?, ?, ?)",
            (
                batch_id,
                json.dumps(spec),
                json.dumps({"generator": ai.GENERATOR_MODEL, "verifier": ai.VERIFIER_MODEL}),
            ),
        )
        conn.commit()

        # -- 1. Generate ----------------------------------------------------
        if spec["kind"] in ("vocab", "vocab_lemmas"):
            if spec["kind"] == "vocab":
                corpus_rows = select_vocab_rows(conn, spec["rank_from"], spec["rank_to"])
            else:
                corpus_rows = select_vocab_rows_by_lemmas(conn, spec["lemmas"])
            if not corpus_rows:
                raise ValueError("no matching lemmas in the corpus")
            prompt = (
                "Corpus rows (the only source of truth):\n"
                + json.dumps(corpus_rows, ensure_ascii=False, indent=1)
                + "\nProduce one card object per lemma, strict JSON array."
            )
            raw, gen_meta = await ai.ask(ai.GENERATOR_MODEL, VOCAB_SYSTEM, prompt)
            candidates = build_vocab_candidates(conn, ai.extract_json(raw), corpus_rows)
        elif spec["kind"] in ("parsing", "parsing_filtered"):
            if spec["kind"] == "parsing":
                corpus_rows = select_parsing_rows(
                    conn, spec["book"], spec["chapter"], spec["parse_like"]
                )
            else:
                corpus_rows = select_parsing_rows_filtered(
                    conn, spec["parse_like"], spec["lemma_in"]
                )
            if not corpus_rows:
                raise ValueError("no tokens match that construction")
            max_cards = int(spec.get("max_cards", 25))
            prompt = (
                "Corpus tokens (the only source of truth):\n"
                + json.dumps(corpus_rows, ensure_ascii=False, indent=1)
                + f"\nSelect up to {max_cards} drill instances, strict JSON array."
            )
            raw, gen_meta = await ai.ask(ai.GENERATOR_MODEL, PARSING_SYSTEM, prompt)
            candidates = build_parsing_candidates(conn, ai.extract_json(raw))
        else:
            raise ValueError(f"unknown spec kind {spec['kind']!r}")

        # -- 2. Validate (programmatic, no model) ---------------------------
        validated: list[dict] = []
        for i, cand in enumerate(candidates):
            reason = validate_candidate(conn, cand)
            if reason is None:
                validated.append(cand)
            else:
                write_reject(batch_id, i, cand, reason, "validate")

        # -- 3. Verify (second model) ---------------------------------------
        verified: list[dict] = []
        verify_meta: dict = {}
        if validated:
            verify_prompt = (
                "Corpus rows:\n"
                + json.dumps(corpus_rows, ensure_ascii=False, indent=1)
                + "\n\nCandidate cards (index order):\n"
                + json.dumps(
                    [{"index": i, **c["payload"]} for i, c in enumerate(validated)],
                    ensure_ascii=False,
                    indent=1,
                )
                + "\nOne verdict per candidate, strict JSON array."
            )
            raw_v, verify_meta = await ai.ask(ai.VERIFIER_MODEL, VERIFY_SYSTEM, verify_prompt)
            verdicts = {v["index"]: v for v in ai.extract_json(raw_v) if isinstance(v, dict)}
            for i, cand in enumerate(validated):
                verdict = verdicts.get(i)
                if verdict is None:
                    write_reject(batch_id, i, cand, "verifier returned no verdict", "verify")
                elif verdict.get("pass") is True:
                    verified.append(cand)
                else:
                    write_reject(
                        batch_id, i, cand, str(verdict.get("reason", "failed")), "verify"
                    )

        # -- 4. Land --------------------------------------------------------
        deck_name = spec.get("deck") or f"Generated {spec['kind']} ({batch_id})"
        deck_row = conn.execute(
            "select id from decks where name = ? and deleted_at is null", (deck_name,)
        ).fetchone()
        deck_id = deck_row["id"] if deck_row else store.create_deck(conn, deck_name, "greek", {})
        for cand in verified:
            store.create_card(
                conn,
                deck_id,
                cand["card_type"],
                cand["payload"],
                source={
                    "citations": cand["citations"],
                    "batch_id": batch_id,
                    "generator_model": ai.GENERATOR_MODEL,
                    "verifier_model": ai.VERIFIER_MODEL,
                    "corpus_id": "sblgnt",
                },
            )
            # backfill validated glosses onto cited tokens that lack one
            gloss = cand["payload"].get("gloss")
            if gloss:
                for tid in cand["citations"]:
                    conn.execute(
                        "update corpus_tokens set gloss = ? where id = ? and gloss is null",
                        (db.nfc(gloss), tid),
                    )

        conn.execute(
            """
            update gen_batches
            set generated=?, validated=?, verified=?, landed=?, finished_at=datetime('now')
            where id=?
            """,
            (len(candidates), len(validated), len(verified), len(verified), batch_id),
        )
        conn.commit()
        return {
            "batch_id": batch_id,
            "deck_id": deck_id,
            "deck_name": deck_name,
            "generated": len(candidates),
            "validated": len(validated),
            "verified_landed": len(verified),
            "rejected": len(candidates) - len(verified),
            "rejects_dir": str(REJECTS_DIR / batch_id),
            "usage": {"generator": gen_meta, "verifier": verify_meta},
        }
    finally:
        conn.close()
