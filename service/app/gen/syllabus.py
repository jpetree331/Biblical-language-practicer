"""Auto-draft the Greek syllabus map from Machen's lesson texts.

Same three-pass discipline as the card pipeline:
  draft (claude-sonnet-5, per lesson) →
  programmatic validation (every lemma must exist in MorphGNT; unambiguous
  near-matches auto-corrected, casualties recorded in the chapter notes;
  concept ids must match the documented convention) →
  second-model verify (claude-opus-5: did the map miss a topic or vocab the
  chapter teaches?) — verifier findings are attached as `verifier_notes`,
  because the draft's consumer is Jess's review, not silent acceptance.

Output: data/syllabus_map.greek.json with "reviewed": false per chapter.
The loader (app/curriculum.py) warns loudly on unreviewed chapters.

Run: scripts\\draft-syllabus.cmd
"""

from __future__ import annotations

import json
import unicodedata

import anyio

from .. import db
from . import ai

MAP_PATH = db.REPO_ROOT / "data" / "syllabus_map.greek.json"

CONCEPT_CONVENTION = """Concept ids follow this convention (compose as needed):
- Verb forms: GK.<TENSE>.<VOICE>.<MOOD> with TENSE in PRES|IMPF|FUT|AOR|AOR2|PERF|PLUP,
  VOICE in ACT|MID|PASS|MP, MOOD in IND|SUBJ|IMPV|INF|PTCP  (e.g. GK.PRES.ACT.IND)
- Declensions: GK.DECL.1 | GK.DECL.2 | GK.DECL.3
- Article: GK.ART ; Adjectives: GK.ADJ (GK.ADJ.COMP for comparison)
- Pronouns: GK.PRON.PERS|DEM|REL|INTERR|INDEF|REFL|RECIP|POSS
- μι-verbs: GK.MI.DIDOMI | GK.MI.TITHEMI | GK.MI.HISTEMI | GK.MI.OTHER
- Other topics: GK.ALPHABET, GK.ACCENT, GK.ENCLIT, GK.CONTRACT, GK.LIQUID,
  GK.NUM, GK.QUESTION, GK.CONDITION, GK.INDIRECT, GK.GENABS, GK.OIDA,
  GK.WORDORDER, GK.CASE.USES — or coin GK.<SHORT.CODE> if truly none fit."""

DRAFT_SYSTEM = f"""You extract a machine-readable syllabus entry from one
lesson of Machen's 1923 "New Testament Greek for Beginners". The text is OCR
and contains corrupted Greek (latin lookalikes, stray accents) — restore
correct polytonic Greek from context.

{CONCEPT_CONVENTION}

Output ONE strict JSON object, nothing else:
{{"title": "<clean lesson title>",
  "concepts": [{{"id": "GK...", "name": "<English name>"}}, ...],
  "vocab_lemmas": ["<dictionary form exactly as a lexicon lemma, polytonic>", ...],
  "notes": "<1-3 sentences: constructions to prefer/avoid when generating
practice for this chapter, e.g. 'introduce only present active; avoid
compound verbs'>"}}

vocab_lemmas = ONLY the words in the lesson's numbered Vocabulary section
(dictionary/lemma form: verbs in 1sg present, nouns in nom. sg.). concepts =
the grammar this lesson TEACHES (not review mentions). Lessons 1-2 (alphabet,
accent) have no vocabulary."""

VERIFY_SYSTEM = """You check syllabus-map entries against the Machen lesson
texts they were extracted from (OCR — tolerate corrupted Greek in the text).
For each entry report extraction fidelity: did the map miss a grammar topic
the lesson teaches, invent one it doesn't, or miss/invent vocabulary?
Output a strict JSON array, one object per lesson, in order:
  {"n": <lesson number>, "ok": true/false, "problems": ["<short finding>", ...]}
ok=true with empty problems when the entry is faithful."""


def _strip(s: str) -> str:
    """Diacritic-free lowercase skeleton for near-matching."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c)
    )


def near_matches(conn, lemma: str, limit: int = 3) -> list[str]:
    skel = _strip(lemma)
    rows = conn.execute("select lemma from lemma_freq where corpus_id='sblgnt'").fetchall()
    exact = [r["lemma"] for r in rows if _strip(r["lemma"]) == skel]
    if exact:
        return exact[:limit]
    # fallback: prefix match on the skeleton
    pref = [r["lemma"] for r in rows if _strip(r["lemma"]).startswith(skel[:4]) and len(skel) > 3]
    return pref[:limit]


def validate_chapter(conn, entry: dict) -> dict:
    """Normalize lemmas against the corpus; record casualties + bad concepts."""
    import re as _re

    fixed_lemmas: list[str] = []
    casualties: list[str] = []
    for lemma in entry.get("vocab_lemmas", []):
        lemma = db.nfc(str(lemma).strip())
        if not lemma:
            continue
        hit = conn.execute(
            "select 1 from lemma_freq where corpus_id='sblgnt' and lemma=?", (lemma,)
        ).fetchone()
        if hit:
            fixed_lemmas.append(lemma)
            continue
        candidates = near_matches(conn, lemma)
        if len(candidates) == 1:
            fixed_lemmas.append(candidates[0])
            casualties.append(f"{lemma} -> auto-corrected to {candidates[0]}")
        else:
            casualties.append(
                f"{lemma} NOT IN CORPUS"
                + (f" (candidates: {', '.join(candidates)})" if candidates else "")
            )
    concepts = []
    for c in entry.get("concepts", []):
        cid = str(c.get("id", "")).strip()
        name = str(c.get("name", "")).strip()
        if _re.fullmatch(r"GK\.[A-Z0-9][A-Z0-9.]*", cid) and name:
            concepts.append({"id": cid, "name": name})
        else:
            casualties.append(f"concept dropped (bad id/name): {c!r}")
    out = dict(entry)
    out["concepts"] = concepts
    out["vocab_lemmas"] = list(dict.fromkeys(fixed_lemmas))  # dedupe, keep order
    out["validation_notes"] = casualties
    return out


async def draft_all() -> dict:
    ai.assert_subscription_auth()
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "select ref, title, body from source_texts where ref like 'machen:%'"
        ).fetchall()
        lessons = sorted(
            ({"n": int(r["ref"].split(":")[1]), "title": r["title"], "body": r["body"]} for r in rows),
            key=lambda x: x["n"],
        )
        if len(lessons) != 33:
            raise RuntimeError(f"expected 33 machen lessons in source_texts, found {len(lessons)}")

        chapters: dict[int, dict] = {}

        async def extract(les: dict) -> None:
            prompt = f"Lesson {les['n']} text:\n\n{les['body'][:9000]}"
            raw, _ = await ai.ask(ai.GENERATOR_MODEL, DRAFT_SYSTEM, prompt)
            entry = ai.extract_json(raw)
            entry["n"] = les["n"]
            chapters[les["n"]] = validate_chapter(conn, entry)
            print(f"  drafted {les['n']:>2}: {len(entry.get('vocab_lemmas', []))} lemmas, "
                  f"{len(entry.get('concepts', []))} concepts")

        # modest concurrency — three lessons in flight
        for wave_start in range(0, len(lessons), 3):
            async with anyio.create_task_group() as tg:
                for les in lessons[wave_start : wave_start + 3]:
                    tg.start_soon(extract, les)

        # verify in batches of 8 chapters
        for batch_start in range(1, 34, 8):
            batch_ns = [n for n in range(batch_start, min(batch_start + 8, 34))]
            payload = []
            for n in batch_ns:
                les = lessons[n - 1]
                ch = chapters[n]
                payload.append(
                    {
                        "n": n,
                        "map_entry": {
                            "title": ch.get("title"),
                            "concepts": ch["concepts"],
                            "vocab_lemmas": ch["vocab_lemmas"],
                        },
                        "lesson_text": les["body"][:7000],
                    }
                )
            raw, _ = await ai.ask(
                ai.VERIFIER_MODEL,
                VERIFY_SYSTEM,
                json.dumps(payload, ensure_ascii=False),
            )
            try:
                verdicts = ai.extract_json(raw)
            except ValueError:
                verdicts = []
            for v in verdicts:
                if isinstance(v, dict) and v.get("n") in chapters:
                    chapters[v["n"]]["verifier_notes"] = (
                        [] if v.get("ok") else [str(p) for p in v.get("problems", [])]
                    ) or ([] if v.get("ok") else ["verifier flagged, no detail"])
            print(f"  verified lessons {batch_ns[0]}-{batch_ns[-1]}")

        doc = {
            "language": "greek",
            "source": "machen-1923",
            "source_is_pd": True,
            "source_provenance": {
                "work": "J. Gresham Machen, New Testament Greek for Beginners, Macmillan, 1923",
                "pd_basis": "published in the USA in 1923; US copyright expired (PD since 2019)",
                "text_url": "https://archive.org/download/newtestamentgree00mach/newtestamentgree00mach_djvu.txt",
                "archive_item": "https://archive.org/details/newtestamentgree00mach",
            },
            "chapters": [
                {
                    "n": n,
                    "title": chapters[n].get("title", lessons[n - 1]["title"]),
                    "concepts": chapters[n]["concepts"],
                    "vocab_lemmas": chapters[n]["vocab_lemmas"],
                    "reading_ref": f"machen:{n}",
                    "notes": chapters[n].get("notes", ""),
                    "validation_notes": chapters[n].get("validation_notes", []),
                    "verifier_notes": chapters[n].get("verifier_notes", []),
                    "reviewed": False,
                }
                for n in sorted(chapters)
            ],
        }
        MAP_PATH.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "chapters": len(doc["chapters"]),
            "total_lemmas": sum(len(c["vocab_lemmas"]) for c in doc["chapters"]),
            "chapters_with_validation_notes": sum(
                1 for c in doc["chapters"] if c["validation_notes"]
            ),
            "chapters_with_verifier_notes": sum(
                1 for c in doc["chapters"] if c["verifier_notes"]
            ),
            "path": str(MAP_PATH),
        }
    finally:
        conn.close()


if __name__ == "__main__":
    db.bootstrap()
    result = anyio.run(draft_all)
    print(json.dumps(result, ensure_ascii=False, indent=2))
