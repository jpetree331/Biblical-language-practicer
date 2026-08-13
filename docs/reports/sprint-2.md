# Sprint 2 — FSRS drill loop

## What shipped

- `service/app/scheduler.py` — the only file that touches py-fsrs:
  - `build_queue(deck_id, limit)`: due reviews (oldest first) + new cards up to
    the deck's `config.newPerDay` budget (default 10, counted against cards
    whose *first-ever* review was today, from `review_log`).
  - `grade(card_id, rating, now=None)`: reconstructs the py-fsrs card from
    `card_state`, applies the rating, writes `card_state` + `review_log` in one
    transaction. The `now` parameter exists for simulation/testing.
  - `deck_stats(deck_id)`: due count, new count, retention estimate (mean
    `get_card_retrievability` over review-state cards).
- Endpoints: `GET /api/review/queue?deck_id=`, `POST /api/review/grade`,
  `GET /api/review/stats?deck_id=`.
- Review page (`#/review/<deckId>`): front → reveal (space or button) → four
  grade buttons Again/Hard/Good/Easy with keys 1–4, session summary
  (reviewed / again-count / best streak). Grade buttons use the reserved
  status colors.
- Deck page now shows due / new / retention, a per-deck **new/day** input
  (writes `config.newPerDay`), and a primary Review button.
- Cloze variants at review time: variant = `reps % variantCount(payload)` —
  each deletion gets its turn across successive reviews. The backend stays
  payload-agnostic; variant selection is a registry concept (Rule 1/6 intact).
- Schema: added `card_state.step` (py-fsrs v6 learning-step index) as an
  idempotent additive migration in `db.bootstrap`.

## Divergences / choices

- py-fsrs v6 has no "New" state — our `card_state.state='new'` marks
  never-reviewed cards; they become fresh `Card()`s at first grade. The DDL's
  four-state text column is unchanged.
- Default scheduler parameters (retention 0.9, fuzzing on). Per-deck desired
  retention is deferred until something needs it.

## What you need to do once

Nothing.

## What's deferred

- Retention threshold config per deck (used by mastery in Sprint 7).
- A "study all decks" combined queue — per-deck queues only for now.

## Verification

- Scratch sim (`sim_fsrs.py`, run through the real `scheduler.grade` code
  path): 30 seeded cards, faked timestamps across days —
  - Good chain intervals grew **2.0d → 5.0d → 21.0d**;
  - Easy scheduled further than Good (11d vs 10d);
  - Again on a review-state card → `relearning`, lapse counted, due in
    **10 minutes**;
  - `review_log` row count exact (65); queue and stats shapes correct
    (retention estimate 0.80 immediately after the fake-day storm, as expected
    for overdue cards).
- Keyboard-only session in the running UI: 3-card Greek deck reviewed start to
  finish with only space and `3`; summary rendered "3 reviewed · 0 again ·
  best streak 3". (Session driven by dispatching real KeyboardEvents.)
- `npm run build` clean; lib tests still 10/10.
