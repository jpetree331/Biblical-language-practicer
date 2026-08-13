# Sprint 7 — Lessons & mastery

## What shipped

- **Lesson assembly** (in the syllabus loader): each chapter gets
  `lesson_items` rows — `read` (ref `machen:N`) → `drill` (vocab deck) →
  `drill` (parsing deck) → `translate`/`compose` placeholders (Sprints 8/9).
  Drill refs use a `deckname:` convention resolved at read time, so
  `build-chapter` can run before or after loading. The `read` item renders
  Machen's full lesson text in-app because `source_texts.source_is_pd=1`;
  a non-PD source falls back to a "Read <book> ch. N" pointer — data-driven,
  no per-language branch (the only place PD touches the UI, per plan).
- **Mastery model, twinned**: `service/app/mastery.py` (source of truth) and
  framework-free `web/src/lib/mastery.ts`, both fixture-tested against
  `shared/mastery-fixtures.json` (19 cases): rating deltas
  (Again −0.15 / Hard +0.02 / Good +0.08 / Easy +0.12, clamped), 90-day
  half-life decay, and `lesson_mastered` = every deck fully at FSRS review
  state with retention ≥ threshold (deck `config.retentionThreshold`,
  default 0.9) AND every *evidenced* concept ≥ 0.8.
- **Registry `on_review` hook** (Rules 1/6 kept intact): the scheduler calls a
  card type's hook generically; the Greek body lives in
  `service/app/greek/mastery_hooks.py` — a `parsing` review maps its parse
  code to `GK.<TENSE>.<VOICE>.<MOOD>` and updates `concept_mastery`
  (decay-then-delta). Only concepts the syllabus created can be updated.
- **Lessons API**: `GET /api/lessons` (statuses, live due counts, auto-flip:
  an active lesson meeting the bar becomes `mastered` and the next locked
  lesson unlocks), `GET /api/lessons/{id}` (resolved items + decayed concept
  scores), `POST /api/lessons/{id}/status` (manual override — Jess outranks
  the model of her own mastery).
- **UI**: Lessons page (spiral-visible list: mastered rows show live due
  counts forever, active highlighted, locked greyed) and Lesson page (item
  sequence with in-app Machen reading, drill links with stats, placeholders
  labeled by sprint; concept mastery bars using the reserved status colors;
  Force-master / Force-unlock / Re-lock buttons).

## Divergences / choices (flagged)

- **Evidence-gated concepts**: concepts nothing can assess yet (e.g.
  `GK.VERB.STEM`, `GK.ALPHABET`) do not block mastery — only concepts with a
  `concept_mastery` row (fed by drills now, the checker in Sprint 8) are
  gated. Without this, non-drillable concepts would lock every lesson forever.
- Lessons 1–2 (alphabet/accent) have no vocab, so no decks — they can only be
  mastered by manual override, which is the honest semantics.
- Concept ids shared across chapters (e.g. GK.PRES.ACT.IND retaught for
  contract verbs in ch. 23) keep one mastery score; the concept's display
  name currently ends up as the *last* chapter's phrasing — cosmetic, noted.

## What you need to do once

Nothing new (the map review from Sprint 6 still stands; mastery starts moving
as soon as you drill parsing decks).

## What's deferred

- `translate`/`compose` items are labeled placeholders until Sprints 8/9.
- Checker-fed concept updates (Sprint 8 wires `submissions` into the same
  `apply_review` path).

## Verification

- Fixtures: **19/19 in Python** and **19/19 in Node** from the shared file —
  the twin implementations agree to 1e-9.
- Live checks against the running service:
  - Lesson 3 items resolve: Machen Lesson III text renders in-app; both ch.3
    decks found with stats.
  - Graded all ch.3 parsing cards Good through the API → the registry hook
    drove **GK.PRES.ACT.IND to 0.88** (10 reviews landed it at exactly 0.80 —
    the threshold boundary — which decay then nudged under: correct, honest
    behavior; the 11th review cleared it).
  - Simulated review-state history on both decks → `GET /api/lessons` flipped
    lesson 3 **active → mastered** and auto-unlocked the next locked lesson.
  - Override cycle re-lock → unlock verified via API; buttons wired in UI.
  - Lessons page renders all 33 with correct status colors (eyeballed via DOM).
- lib tests 26/26; `npm run build` clean.
