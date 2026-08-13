"""Exercise generation — translate_gk_en (Sprint 8) and compose (Sprint 9).

Passages are REAL corpus verses selected by SQL for vocabulary coverage
against the syllabus map (chapters 1..N introduced lemmas). The model never
picks the Greek; it only renders the answer key English, which a second model
verifies. Answer keys carry the passage's token ids as citations.
"""

from __future__ import annotations

import json
import uuid

from .. import db
from . import ai

ANSWER_KEY_SYSTEM = """You are preparing answer keys for beginner Koine Greek
translation exercises. For each passage you receive the full token rows
(surface, lemma, parse, position) — the only source of truth. Produce a
natural but fairly literal English rendering a beginner could be measured
against. Output a strict JSON array, one object per passage, in order:
  {"index": <i>, "english": "<rendering>"}"""

ANSWER_KEY_VERIFY = """You are checking English answer keys for Koine Greek
passages against their token rows. Fail a rendering that mistranslates,
omits, or adds content (minor naturalness choices are fine). Output a strict
JSON array: {"index": <i>, "pass": true/false, "reason": "<one line>"}"""

COMPOSE_PROMPT_SYSTEM = """You are preparing English prompts for
English→Greek composition exercises. Each item's Greek answer is an attested
New Testament sentence (token rows supplied — the only source of truth).
Write the English prompt a student will translate INTO Greek: natural
English, no Greek characters, no hints about word order. Output a strict JSON
array: {"index": <i>, "english": "<prompt>"}"""


def known_lemmas_through(map_doc: dict, chapter_n: int) -> set[str]:
    return {
        lem
        for ch in map_doc["chapters"]
        if ch["n"] <= chapter_n
        for lem in ch.get("vocab_lemmas", [])
    }


def candidate_verses(
    conn, known: set[str], min_ratio: float, min_tokens: int, max_tokens: int, limit: int
) -> list[dict]:
    """Verses ranked by share of tokens whose lemma is known."""
    rows = conn.execute(
        """
        select book, chapter, verse, count(*) as n
        from corpus_tokens where corpus_id='sblgnt'
        group by book, chapter, verse
        having n between ? and ?
        """,
        (min_tokens, max_tokens),
    ).fetchall()
    scored = []
    for r in rows:
        tokens = conn.execute(
            """
            select id, pos, surface, lemma, parse, gloss from corpus_tokens
            where corpus_id='sblgnt' and book=? and chapter=? and verse=?
            order by pos
            """,
            (r["book"], r["chapter"], r["verse"]),
        ).fetchall()
        known_count = sum(1 for t in tokens if t["lemma"] in known)
        ratio = known_count / len(tokens)
        if ratio >= min_ratio:
            scored.append(
                {
                    "ref": f"{r['book']}.{r['chapter']}.{r['verse']}",
                    "ratio": ratio,
                    "tokens": [dict(t) for t in tokens],
                }
            )
    scored.sort(key=lambda v: -v["ratio"])
    return scored[:limit]


def _passage_payload(v: dict, known: set[str]) -> dict:
    return {
        "ref": v["ref"],
        "token_ids": [t["id"] for t in v["tokens"]],
        "tokens": [
            {
                "id": t["id"],
                "pos": t["pos"],
                "surface": t["surface"],
                "lemma": t["lemma"],
                "parse": t["parse"],
                "gloss": t["gloss"],
                "known": t["lemma"] in known,
            }
            for t in v["tokens"]
        ],
    }


async def build_exercises(
    language: str, chapter_n: int, count: int = 3, kinds: tuple = ("translate_gk_en", "compose")
) -> dict:
    ai.assert_subscription_auth()
    map_path = db.REPO_ROOT / "data" / f"syllabus_map.{language}.json"
    map_doc = json.loads(map_path.read_text(encoding="utf-8"))
    known = known_lemmas_through(map_doc, chapter_n)
    if not known:
        raise ValueError(f"no lemmas known through chapter {chapter_n}")

    conn = db.get_conn()
    try:
        lesson = conn.execute(
            "select id from lessons where seq = ?", (chapter_n,)
        ).fetchone()
        lesson_id = lesson["id"] if lesson else None

        made = {k: 0 for k in kinds}
        rejected = []

        for kind in kinds:
            if kind == "translate_gk_en":
                verses = candidate_verses(conn, known, 0.85, 6, 22, count * 2)
            else:  # compose: shorter, tighter coverage
                verses = candidate_verses(conn, known, 0.9, 4, 12, count * 2)
            verses = verses[:count]
            if not verses:
                continue

            passages_for_model = [
                {"index": i, "ref": v["ref"], "tokens": [
                    {"pos": t["pos"], "surface": t["surface"], "lemma": t["lemma"], "parse": t["parse"]}
                    for t in v["tokens"]
                ]}
                for i, v in enumerate(verses)
            ]
            system = ANSWER_KEY_SYSTEM if kind == "translate_gk_en" else COMPOSE_PROMPT_SYSTEM
            raw, _ = await ai.ask(
                ai.GENERATOR_MODEL, system, json.dumps(passages_for_model, ensure_ascii=False)
            )
            renderings = {
                item["index"]: item["english"]
                for item in ai.extract_json(raw)
                if isinstance(item, dict) and isinstance(item.get("english"), str)
            }

            # verify the English against the tokens
            verify_payload = [
                {**p, "english": renderings.get(p["index"], "")} for p in passages_for_model
            ]
            raw_v, _ = await ai.ask(
                ai.VERIFIER_MODEL, ANSWER_KEY_VERIFY, json.dumps(verify_payload, ensure_ascii=False)
            )
            verdicts = {
                v["index"]: v for v in ai.extract_json(raw_v) if isinstance(v, dict)
            }

            for i, verse in enumerate(verses):
                english = renderings.get(i)
                verdict = verdicts.get(i, {})
                if not english or verdict.get("pass") is not True:
                    rejected.append(
                        {"kind": kind, "ref": verse["ref"], "reason": verdict.get("reason", "no rendering")}
                    )
                    continue
                payload = _passage_payload(verse, known)
                if kind == "translate_gk_en":
                    prompt = payload
                    answer_key = {"english": english, "citations": payload["token_ids"]}
                else:
                    prompt = {"english": english, "ref": verse["ref"], "token_ids": payload["token_ids"]}
                    answer_key = {
                        "greek": " ".join(t["surface"] for t in verse["tokens"]),
                        "tokens": payload["tokens"],
                        "citations": payload["token_ids"],
                    }
                conn.execute(
                    """
                    insert into exercises (id, lesson_id, kind, prompt, answer_key)
                    values (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        lesson_id,
                        kind,
                        json.dumps(prompt, ensure_ascii=False),
                        json.dumps(answer_key, ensure_ascii=False),
                    ),
                )
                made[kind] += 1
        conn.commit()
        return {"chapter": chapter_n, "made": made, "rejected": rejected, "known_lemmas": len(known)}
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    import anyio

    parser = argparse.ArgumentParser(prog="app.gen.exercises")
    parser.add_argument("language")
    parser.add_argument("chapter", type=int)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    db.bootstrap()
    print(json.dumps(anyio.run(build_exercises, args.language, args.chapter, args.count), ensure_ascii=False, indent=2))
