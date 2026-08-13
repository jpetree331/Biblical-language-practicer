"""Split the Machen 1923 OCR text into lessons.

Source: Internet Archive item `newtestamentgree00mach` — Machen,
*New Testament Greek for Beginners*, Macmillan, 1923. Published 1923 in the
US, so its copyright expired; the work is public domain (GATE C). The raw
OCR file lives at data/machen/machen-1923-djvu.txt (gitignored; re-download
from https://archive.org/download/newtestamentgree00mach/newtestamentgree00mach_djvu.txt).

OCR quirks handled here: lesson headings sometimes use Greek homoglyphs
("LESSON ΙΧ"), trailing junk, or go missing entirely — so headings are
detected loosely and lessons are numbered by ORDER of appearance, then
sanity-checked against the roman numeral when it parses.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import db

SOURCE_PATH = db.REPO_ROOT / "data" / "machen" / "machen-1923-djvu.txt"

# Greek capital homoglyphs the OCR substitutes for latin letters in numerals
_HOMOGLYPHS = str.maketrans("ΙΧΝΜ", "IXVM")  # Ι->I, Χ->X, Ν->V is wrong; see below

_ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
    "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21,
    "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25, "XXVI": 26, "XXVII": 27,
    "XXVIII": 28, "XXIX": 29, "XXX": 30, "XXXI": 31, "XXXII": 32, "XXXIII": 33,
}


def _roman_to_int(token: str) -> int | None:
    cleaned = token.translate(str.maketrans("ΙΧ", "IX")).strip(" .;:,")
    return _ROMAN.get(cleaned)


def split_lessons(text: str | None = None) -> list[dict]:
    """Return [{n, title, body}] for the 33 lessons, ordered."""
    if text is None:
        text = SOURCE_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    # find heading lines: short lines containing "LESSON <numeral-ish>",
    # tolerating OCR junk before/after ("_ LESSON XXI", "LESSON XXV ;",
    # "ἦ LESSON ΧΧΙΧ" with Greek homoglyph capitals)
    heads: list[tuple[int, int | None]] = []  # (line index, parsed numeral)
    for i, line in enumerate(lines):
        if len(line) > 30 or "LESSON" not in line:
            continue
        m = re.search(r"LESSON\s+([A-ZΙΧΝ]+)", line)
        if m:
            heads.append((i, _roman_to_int(m.group(1))))

    # keep only the sequence that starts at lesson 1 (skips TOC noise)
    start = next((k for k, (_i, n) in enumerate(heads) if n == 1), 0)
    heads = heads[start:]

    lessons: list[dict] = []
    for k, (line_idx, parsed_n) in enumerate(heads):
        seq_n = k + 1  # order of appearance is authoritative (OCR drops some numerals)
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        title = ""
        for j in range(line_idx + 1, min(line_idx + 6, end)):
            if lines[j].strip():
                title = lines[j].strip()
                break
        body = "\n".join(lines[line_idx:end]).strip()
        lessons.append(
            {
                "n": seq_n,
                "numeral_parsed": parsed_n,
                "numeral_matches": parsed_n == seq_n if parsed_n else None,
                "title": title,
                "body": db.nfc(body),
            }
        )
    return lessons


def store_source_texts(lessons: list[dict], source_is_pd: bool = True) -> int:
    """Write lessons into source_texts as machen:N. PD-only by construction —
    the loader separately refuses non-PD rows (the guardrail lives there)."""
    conn = db.get_conn()
    try:
        for les in lessons:
            conn.execute(
                """
                insert into source_texts (ref, title, body, source_is_pd)
                values (?, ?, ?, ?)
                on conflict(ref) do update set title=excluded.title,
                  body=excluded.body, source_is_pd=excluded.source_is_pd
                """,
                (f"machen:{les['n']}", les["title"], les["body"], 1 if source_is_pd else 0),
            )
        conn.commit()
        return len(lessons)
    finally:
        conn.close()


if __name__ == "__main__":
    db.bootstrap()
    lessons = split_lessons()
    print(f"split {len(lessons)} lessons")
    for les in lessons:
        flag = "" if les["numeral_matches"] in (True, None) else "  <-- numeral mismatch, check"
        print(f"  {les['n']:>2}: {les['title'][:60]}{flag}")
    stored = store_source_texts(lessons)
    print(f"stored {stored} lessons into source_texts")
