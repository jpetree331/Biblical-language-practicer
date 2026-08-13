# Sprint 3 — Verse memory + import/export (generic engine ships here)

## What shipped

- **Card type `verse`** `{reference, translation?, text, graduateAfter}` in both
  registries. Review rendering graduates per card: while `reps <
  graduateAfter` the front shows the reference plus a **first-letters** hint
  (`I t b w t W…`); at `graduateAfter` and beyond it asks for recitation from
  the reference alone. The back is always the full text.
  - *Fable's pick (plan delegated it):* the graduation threshold lives in the
    **payload** (`graduateAfter`, default 6, editable per card in the editor),
    and progress is measured by `reps` from `card_state`, passed to renderers
    as a `ReviewCtx` — no per-type branching anywhere outside the registry.
- `web/src/lib/firstLetters.ts` — Unicode-aware (Greek diacritics stay on the
  first letter: `ἐν ἀρχῇ…` → `ἐ ἀ…`), framework-free, tested.
- **Export**: `GET /api/decks/{id}/export` → canonical JSON
  (`format: "scriptorium-deck@1"`) carrying deck config + every card's payload,
  source, and full FSRS state. Deck page has Export (JSON) and CSV (basic
  cards) buttons.
- **Import** (`#/import`, nav link): JSON or CSV (client-side parse via
  framework-free `lib/csv.ts`, RFC-4180, header optional), **parse-then-confirm**
  — preview shows deck name, per-type counts, how many cards keep their review
  schedule, and every skipped-row/skipped-card warning; nothing is written
  until Confirm.
- Decks page groups decks by topic with section headers.
- `README.md` rewritten for Jess-the-user: starting the app, card types,
  review keys, import/export, what the Greek phases will add.

## Divergences / choices

- CSV import/export intentionally minimal (basic cards only) per plan; JSON is
  canonical.
- Import always creates a **new** deck (no merge-into-existing) — simplest
  correct semantics for restore; merge can come later if wanted.

## What you need to do once

Nothing. (If you want the app always-on, the Task Scheduler recipe is in
RUNBOOK.md.)

## What's deferred

- Verse cards inside the *cloze* full-recite variant (plan mentioned
  "full-cloze" as one rendering; recitation-from-reference covers the same
  memory work — flag if you want a word-by-word blank mode too).

## Verification

- Real decks built and drilled through the API + UI:
  - **John 1 (KJV), 5 verse cards** (public domain) — drilled; first-letters
    front confirmed at `reps=1`, graduated "recite from memory" front
    confirmed at `reps=2` (graduateAfter=2), full text on reveal.
  - **Chem constants, 10 basic cards** — drilled clean.
- **Export → wipe → import round-trip**: exported the science deck, soft-deleted
  it, previewed (10 cards, 10 with FSRS state, zero warnings), committed, and
  re-exported — stability/state/reps tuples **byte-equal before vs after**.
- Corrupted import doc (payload replaced with nonsense) → card skipped with a
  named warning, 9/10 imported, no crash.
- lib tests **18/18** in plain Node; `npm run build` clean.
- Found & fixed during verify: Vite's watcher had served a stale transform
  after two rapid edits to one file — not an app bug (a `touch` re-synced);
  noting it as a dev-loop quirk to watch for.

**Phase 1 exit reached:** Scriptorium is a usable general flashcard app with
proper spaced repetition. Jess can live in it while Phases 2–3 are built.
