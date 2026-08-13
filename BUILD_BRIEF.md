# BUILD_BRIEF.md — Scriptorium (codename: Scriptorium)

> Standing brief for every sprint. Source: `scriptorium_master_plan.md`.
> Divergences from the master plan, locked at Sprint 0: repo lives at
> `E:\git\Language-Learning` (pushed to `jpetree331/Biblical-language-practicer`)
> instead of `E:\git\scriptorium`; Python is 3.13 (3.12 not installed on
> dreammachine). All paths below reflect the real repo root.

## Stack & environment

- Windows 11 Pro, repo at `E:\git\Language-Learning`. Target machine: dreammachine (Ryzen 9 7950X3D, 64GB, RTX 4090 — GPU irrelevant here).
- Frontend: Vite + React 19 + TypeScript, port **5180**, hand-written design-token CSS (`web/src/theme.css`), no Tailwind, no component libraries.
- Backend: FastAPI (Python 3.13), port **8012**, run via uvicorn. SQLite (stdlib `sqlite3`, `Row` factory, WAL mode) at `data/scriptorium.db`. Raw SQL, no ORM.
- Scheduling: `py-fsrs` (PyPI package `fsrs`). AI: `claude-agent-sdk` (Python), subscription auth via Claude Code login.
- All Python entrypoints run with `PYTHONUTF8=1`. `.cmd` wrappers in `scripts/` for Task Scheduler.
- Pinned versions (locked at Sprint 0 — see `docs/reports/sprint-0.md`): react 19.2.8, vite 8.2.0, typescript 6.0.2, fastapi 0.141.1, uvicorn 0.52.3, fsrs 6.3.2, claude-agent-sdk 0.2.137.

## The autonomy clause (applies to every sprint)

Work autonomously to completion. Do not stop to ask for confirmation on reversible implementation choices — pick the sound default, note it in your summary, and keep going. Never: change the locked stack, add paid services, set `ANTHROPIC_API_KEY`, or weaken the citation-validation guardrail without flagging.

## The Recon → Build → Verify contract

Every sprint runs RECON (read before writing), BUILD, VERIFY (do this, don't skip), and reports divergences from the plan in the sprint report.

## Divergence rules (do NOT break these without flagging)

1. **No per-card-type branching in components or endpoints.** Card types live in the registry (`web/src/config/cardTypes.ts` frontend, `service/app/card_types.py` backend): renderer, payload schema, grading mode. Adding a card type = adding a registry entry.
2. **`web/src/lib/` is framework-free** — no React imports, no fetch. Pure logic (transliteration, payload validation, mastery math) so it unit-tests in plain Node. Say so in file headers.
3. **The drill loop never calls a model.** Reviews are served and graded entirely from SQLite + FSRS.
4. **Nothing AI-generated is stored, and no AI correction is displayed, without passing citation validation.** Failed items go to `docs/generation/rejects/` with the failure reason — never silently dropped, never silently shown.
5. **`ANTHROPIC_API_KEY` is never set** in `.env`, `.cmd` wrappers, or the service environment. Subscription auth only.
6. **The deck engine stays topic-agnostic.** Greek-specific logic lives in `service/app/greek/` and `web/src/config/cardTypes.ts` entries — never in deck/review core.

## Schema (source of truth — DDL sketch, adapt idiomatically; SQLite dialect)

```sql
-- decks & cards (generic engine)
create table if not exists decks (
  id text primary key,            -- uuid, client- or server-generated
  name text not null,
  topic text not null default 'general',
  config text not null default '{}',   -- json: per-deck settings
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  deleted_at text                      -- soft delete tombstone
);

create table if not exists cards (
  id text primary key,
  deck_id text not null references decks(id),
  card_type text not null,             -- key into the card-type registry
  payload text not null,               -- json, schema per card_type
  source text,                         -- json: provenance + corpus citations
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  deleted_at text
);

-- FSRS state + log
create table if not exists card_state (
  card_id text primary key references cards(id),
  stability real, difficulty real,
  due text not null,                   -- iso datetime
  last_review text,
  reps integer not null default 0,
  lapses integer not null default 0,
  state text not null default 'new'    -- new|learning|review|relearning
);

create table if not exists review_log (
  id text primary key,
  card_id text not null references cards(id),
  rating integer not null,             -- 1..4 (again/hard/good/easy)
  reviewed_at text not null default (datetime('now')),
  elapsed_days real, scheduled_days real
);

-- corpus (Greek now; corpus_id seam for Hebrew later)
create table if not exists corpora (
  id text primary key, name text not null, license text not null
);
create table if not exists corpus_tokens (
  id integer primary key,
  corpus_id text not null references corpora(id),
  book text not null, chapter integer not null, verse integer not null,
  pos integer not null,                -- word position in verse
  surface text not null,               -- as printed
  normalized text not null,
  lemma text not null,
  parse text not null,                 -- MorphGNT parse code, stored verbatim
  gloss text                           -- filled by generation pipeline, validated
);
create table if not exists lemma_freq (
  corpus_id text not null, lemma text not null,
  count integer not null, rank integer not null,
  primary key (corpus_id, lemma)
);

-- curriculum
create table if not exists concepts (
  id text primary key,                 -- e.g. 'GK.PRES.ACT.IND'
  name text not null,
  chapter_ref text                     -- source chapter that introduces it
);
create table if not exists lessons (
  id text primary key,
  seq integer not null unique,
  title text not null,
  chapter_ref text,                    -- 'machen:12'
  status text not null default 'locked'  -- locked|active|mastered
);
create table if not exists lesson_items (
  id text primary key,
  lesson_id text not null references lessons(id),
  kind text not null,                  -- read|drill|translate|compose
  ref text not null,                   -- deck id, exercise id, or passage ref
  seq integer not null
);
create table if not exists concept_mastery (
  concept_id text primary key references concepts(id),
  score real not null default 0,       -- 0..1, decays; updated by drills+checks
  updated_at text not null default (datetime('now'))
);

-- exercises + Jess's submissions + checker output
create table if not exists exercises (
  id text primary key,
  lesson_id text references lessons(id),
  kind text not null,                  -- translate_gk_en|translate_en_gk|compose
  prompt text not null,                -- json: passage refs, english prompt, constraints
  answer_key text,                     -- json: reference rendering + citations
  created_at text not null default (datetime('now'))
);
create table if not exists submissions (
  id text primary key,
  exercise_id text not null references exercises(id),
  answer text not null,
  feedback text,                       -- json: checker output, post-validation
  score real,
  submitted_at text not null default (datetime('now'))
);
```

## Guardrails carried throughout

- Defensive-load sanitizers on every payload read from SQLite (`safePayload(cardType, raw)` coercing to registry defaults) — corrupt rows must never crash the app.
- `makeId(prefix)` helper with non-secure-context fallback (`crypto.randomUUID` is unavailable on plain-HTTP LAN).
- Unicode: all files UTF-8, `PYTHONUTF8=1` everywhere, Greek stored NFC-normalized; test polytonic Greek (ᾧ, ῥῆμα) round-trips through API + DB + render in Sprint 0's VERIFY.
- Backups: the SQLite file lives under `data/`; `scripts/backup.cmd` zips `data/` to `backups\` — consistent with the zip-at-repo-root backup habit.
- Sprint reports to `docs/reports/sprint-N.md`, shape: What shipped / What you need to do once / What's deferred / Verification.
