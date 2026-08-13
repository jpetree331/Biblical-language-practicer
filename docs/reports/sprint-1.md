# Sprint 1 — Decks, cards, card-type registry

## What shipped

- **Backend CRUD**: `POST/GET/PATCH/DELETE /api/decks`, `GET /api/decks/{id}/cards`,
  `POST/PATCH/DELETE /api/cards`. All SQL lives in `service/app/store.py` as small
  query functions; route bodies stay thin (per plan). Soft delete via
  `deleted_at` tombstones on both decks and cards. Every created card gets an
  FSRS `card_state` row (new, due now) so Sprint 2 has nothing to backfill.
- **Card-type registries, both sides** (Divergence Rule 1 — zero per-type
  branching anywhere else):
  - `service/app/card_types.py`: JSON Schema per type + structural checks
    (cloze deletion ranges validated: in-range, ordered, non-overlapping).
    Writes reject invalid payloads with 422 + reasons.
  - `web/src/config/cardTypes.tsx`: per-type editor field specs, payload↔field
    conversion, defensive `sanitize`, `variantCount` (cloze: one review per
    deletion), `renderFront`/`renderBack`, `summarize`. Unknown card types
    degrade to a placeholder basic card instead of crashing.
- **Launch types**: `basic` `{front, back, hint?}` and `cloze`
  `{text, deletions:[{start,end}]}`. Cloze authoring uses `[[double bracket]]`
  markup, converted to codepoint offsets by `lib/clozeSplit.ts`.
- **Frontend**: hash routing (`web/src/hooks/useHashRoute.ts`, hand-rolled — no
  router dependency), Decks page (tile grid + counts + inline create), Deck page
  (card list with type tags + summaries, generic add/edit modal, rename,
  delete), About page (health + the polytonic canary).
- **`web/src/lib/` is framework-free** (Divergence Rule 2, stated in file
  headers): `ids.ts` (`makeId` with non-secure-context fallback), `sanitize.ts`
  (`safePayload` — structural coercion to registry defaults), `clozeSplit.ts`
  (markup parse/serialize + segment split).

## Divergences / choices

- Routing is hand-rolled hash routing rather than react-router — keeps the
  dependency set at the Sprint 0 pins; three routes don't justify a router.
- Node 22.18's built-in type-stripping runs the lib tests directly
  (`node --test src/lib/*.test.ts`) — no Vitest dependency needed. Test files
  import with explicit `.ts` extensions (Node ESM requirement).
- Removed remaining Vite-template assets; added a small Σ favicon.

## What you need to do once

Nothing.

## What's deferred

- Review flow + keyboard shortcuts (Sprint 2).
- Deck config UI (`newPerDay` etc.) — config field exists and round-trips;
  surfaced in Sprint 2 alongside the queue.

## Verification

- Created a deck; added a basic card (Greek front `λόγος`) and a cloze card
  (`ἐν ἀρχῇ ἦν ὁ λόγος` with two deletions) through the API; edited the basic
  card; invalid cloze (deletion past end of text) rejected with **422**;
  soft-deleted the cloze (list shrank 2→1); hand-restored it in SQLite
  (list back to 2).
- Hand-corrupted the basic card's payload in SQLite
  (`{"front": 12345, "junk": true}`) → Deck page renders
  "(missing front) → (missing back)", no crash (confirmed in the running UI).
- `node --test src/lib/*.test.ts`: **10/10 pass** in plain Node — the
  framework-free seam holds.
- `npm run build` (tsc + vite) clean.
