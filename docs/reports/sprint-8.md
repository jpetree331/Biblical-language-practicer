# Sprint 8 — Reading & translation + the checker

## What shipped

- **Exercise generation** (`service/app/gen/exercises.py`,
  `scripts\build-exercises.cmd greek N`): passages are *real corpus verses*
  selected by SQL for vocabulary coverage — a verse qualifies when ≥85% of its
  tokens' lemmas are introduced by chapters 1..N (the model never picks the
  Greek). Answer keys are Sonnet-rendered English **verified by Opus** before
  storing; rejects are reported, not stored. Exercises carry the passage's
  full token rows and token-id citations.
- **Reading/translate page** (`#/exercise/<id>`): the passage in Greek,
  tap-a-word → lemma + decoded parse + gloss **straight from MorphGNT — no
  model call** (footnoted as such in the UI), textarea, submit.
- **The checker** (`service/app/greek/checker.py`, claude-opus-5): receives
  the submission + the passage's full token rows inline + the answer key;
  returns strict JSON — score, one-line summary, and per-token notes
  (`error`/`nitpick`/`praise`), each carrying a `token_id` and a
  `claimed_parse`.
- **Programmatic validation before display** (Divergence Rule 4 at full
  strength): a note citing a token outside the passage, or claiming a parse
  that disagrees with the stored code, is **withheld** — logged to
  `docs/generation/rejects/checker/`, counted, and surfaced in the UI as
  "N notes were withheld (failed verification)". Silence is visible.
- Every displayed note is footnoted **"checked against MorphGNT <ref>"**.
- **Concept feedback**: each verb token in the passage rates its
  `GK.<T>.<V>.<M>` concept — 1 if an error note tagged it, else 3 — through
  the same shared mastery functions the drills use.
- Lesson pages now list their translate/compose exercises with last scores.

## What you need to do once

Nothing (exercises for a chapter appear when you run
`build-exercises.cmd greek N` — worth doing per chapter as you reach it).

## What's deferred

- Per-clause (rather than per-token) verdict granularity.
- Checker-note deep-links into the corpus browser (the ref footnote names the
  verse; a click-through is cosmetic work).

## Verification (real checker runs, real models)

- Generated for chapter 8 (74 known lemmas): 2 translate + 2 compose, zero
  rejects — passages **John 1:1, Acts 13:30, John 1:4** (genuinely attested,
  coverage-selected).
- **Deliberately wrong translation** of John 1:1 ("Into the beginning… the
  word was against God"): score 0.55; the checker flagged ἐν+dative rendered
  as "into", πρός+accusative as "against", and the anarthrous-θεός
  subject point — every note tagged `error`, cited a token that resolves, and
  footnoted MorphGNT John.1.1. Zero withheld.
- **Correct-but-unusual translation** (NEB-flavored), run twice: 0.88 with no
  errors, then 0.92 with one — the second run rated "dwelt" for ἦν an error
  rather than a nitpick. No *invented* grammar errors in either run; the
  instability is severity-of-judgment on a genuinely loose rendering
  (noted per plan).
- **Tamper test**: hand-forged notes — out-of-passage token id → withheld
  ("token id 999999 is not in this passage"); contradicting parse claim →
  withheld ("claimed parse 'V- 3AAI-S--' != stored 'P- --------'"); the
  legitimate control note survived. UI renders the withheld count.
- Concept updates confirmed (GK.IMPF.ACT.IND fed by the John 1:1 checks).
