# Scriptorium — Master Build Plan
*A generalized FSRS flashcard engine + AI-generated Biblical Greek curriculum, local-first on dreammachine.*

## Locked decisions (do not relitigate)

- **Codename: Scriptorium.** Repo at `E:\git\scriptorium`.
- **Two processes.** Frontend: Vite + React + TypeScript on **port 5180**. Backend: FastAPI local service on **port 8012**. Both ports are new claims — document them in the RUNBOOK.
- **SQLite, not Postgres/Supabase.** Deliberate deviation from the usual product-app archetype: single-user, fully local, drill loop must work offline, and no new Supabase projects (out of free tier, Aug 2026). DB file at `E:\git\scriptorium\data\scriptorium.db`, WAL mode. No auth, no RLS — trust boundary is the machine.
- **AI access: `claude-agent-sdk` (Python) inside the FastAPI service, subscription auth.** `ANTHROPIC_API_KEY` must never be set in this project's environment — if it is, the SDK silently bills API credits instead of the Max plan's Agent SDK credit. The `.env.example` says this in a shouting comment.
- **FSRS via `py-fsrs`, server-side.** The scheduler is the spiral method: every mastered item resurfaces on its forgetting curve indefinitely. No hand-rolled scheduling.
- **Generic deck engine first, Greek second.** Card types are data-driven via a registry (`src/config/cardTypes.ts` + matching backend registry). Lessons, corpus, and generation are layers that *reference* decks; the deck engine never knows about Greek.
- **Grounding is mandatory.** Generated Greek content and checker corrections must cite corpus token IDs, and citations are programmatically validated before anything is stored or displayed. This is a Divergence Rule, not an aspiration.
- **Styling: hand-written design-token CSS** (`src/theme.css`), no Tailwind, no component library. Warm/bookish fonts (suggested: Playfair Display for headings, Libre Franklin for UI, SBL Greek or Noto Serif via `@font-face` for Greek text — Greek font choice is Fable's to make, noted in the sprint report). Reserve green/amber/red for mastery status only.
- **Versions: pin at scaffold.** React 19.x, Vite (current major at scaffold — her repos have drifted to 8), TypeScript 5.x, Python 3.12, FastAPI current, `py-fsrs` current, `claude-agent-sdk` current. Fable records exact pinned versions in the Sprint 0 report; they are then locked.
- **Deployment: local only.** Windows Task Scheduler + `.cmd` wrappers with `PYTHONUTF8=1` (non-negotiable — Greek/Hebrew text will corrupt without it). No Docker, no Vercel, no CI.
- **Corpus: MorphGNT SBLGNT** (tagged Greek NT) ingested into SQLite. Respect and record its license at ingest time (check the repo's LICENSE, attribute in README). Hebrew (OSHB) is a **seam only** — schema accommodates a second corpus, zero implementation until Greek works end to end.
- **Each language gets a syllabus map; the book anchors sequence, not content — unless it's public domain.** `data/syllabus_map.<lang>.json` maps chapters to grammar concept codes + vocab lemmas. **Greek: Machen, *New Testament Greek for Beginners* (1923, public domain — GATE C).** Because Machen is PD, Fable auto-drafts the Greek map from the book's own text and may include Machen's explanations/readings in-app as lesson reading content; Jess reviews the draft rather than authoring it. **Hebrew (future phase): Dobson's *Learn Biblical Hebrew* (Jess owns it, in copyright)** — hand-built map, "Read Dobson ch. N" pointer only, no book text in the app. The PD/in-copyright distinction is a guardrail, not a style choice.

## How to run this plan

Paste one sprint block at a time into Claude Code at `E:\git\scriptorium`. Save the Standing Brief below as `BUILD_BRIEF.md` in Sprint 0. Each sprint ends with a report at `docs/reports/sprint-N.md` (shape: What shipped / What you need to do once / What's deferred / Verification). Commits map 1:1 to sprints: `Sprint 3: verse-memory cards + deck import`.

Phases:
- **Phase 1 — Generic deck engine** (Sprints 0–3): a usable any-topic FSRS flashcard app.
- **Phase 2 — Corpus & generation** (Sprints 4–6): MorphGNT ingest, the generation + verification pipeline, Machen syllabus map (auto-drafted, Jess-reviewed).
- **Phase 3 — Lesson engine** (Sprints 7–9): lessons, mastery, AI checking of Jess's work, composition.
- **Phase 4 — Horizon** (Sprint 10+): graded NT reader; Hebrew seam.

⚠️ **Decision gates:**
- **GATE A** (resolve before Sprint 5): model pair for generation vs. verification. Default: Sonnet generates, a different model verifies (mirrors Jess's build/verify model split). Jess confirms or swaps.
- **GATE B** (resolve before Sprint 9): Greek input for composition. Default: transliteration widget (`logos` → λόγος live preview) with beta-code fallback. Alternative: OS Greek Polytonic keyboard, no widget.
- **GATE C** (resolve before Sprint 6): Greek syllabus source. Default: Machen (1923, PD, auto-draftable, in-app readable). Alternatives: a Claude-authored sequence (viable — verifier checks concept coverage, but no ground truth exists for *ordering*, so this is the weaker option), or Dobson NT Greek if the book turns up (reverts Greek to pointer-only mode like Hebrew).

---

# STANDING BRIEF (save as `BUILD_BRIEF.md`)

# BUILD_BRIEF.md — Scriptorium (codename: Scriptorium)

## Stack & environment

- Windows 11 Pro, repo at `E:\git\scriptorium`. Target machine: dreammachine (Ryzen 9 7950X3D, 64GB, RTX 4090 — GPU irrelevant here).
- Frontend: Vite + React 19 + TypeScript, port **5180**, hand-written design-token CSS (`src/theme.css`), no Tailwind, no component libraries.
- Backend: FastAPI (Python 3.12), port **8012**, run via uvicorn. SQLite (stdlib `sqlite3`, `Row` factory, WAL mode) at `data/scriptorium.db`. Raw SQL, no ORM.
- Scheduling: `py-fsrs`. AI: `claude-agent-sdk` (Python), subscription auth via Claude Code login.
- All Python entrypoints run with `PYTHONUTF8=1`. `.cmd` wrappers in `scripts/` for Task Scheduler.
- Pin exact dependency versions at scaffold; record them in the Sprint 0 report; treat as locked thereafter.

## The autonomy clause (applies to every sprint)

Work autonomously to completion. Do not stop to ask for confirmation on reversible implementation choices — pick the sound default, note it in your summary, and keep going. Never: change the locked stack, add paid services, set `ANTHROPIC_API_KEY`, or weaken the citation-validation guardrail without flagging.

## The Recon → Build → Verify contract

Every sprint runs RECON (read before writing), BUILD, VERIFY (do this, don't skip), and reports divergences from the plan in the sprint report.

## Divergence rules (do NOT break these without flagging)

1. **No per-card-type branching in components or endpoints.** Card types live in the registry (`src/config/cardTypes.ts` frontend, `app/card_types.py` backend): renderer, payload schema, grading mode. Adding a card type = adding a registry entry.
2. **`src/lib/` is framework-free** — no React imports, no fetch. Pure logic (transliteration, payload validation, mastery math) so it unit-tests in plain Node. Say so in file headers.
3. **The drill loop never calls a model.** Reviews are served and graded entirely from SQLite + FSRS.
4. **Nothing AI-generated is stored, and no AI correction is displayed, without passing citation validation.** Failed items go to `docs/generation/rejects/` with the failure reason — never silently dropped, never silently shown.
5. **`ANTHROPIC_API_KEY` is never set** in `.env`, `.cmd` wrappers, or the service environment. Subscription auth only.
6. **The deck engine stays topic-agnostic.** Greek-specific logic lives in `app/greek/` and `src/config/cardTypes.ts` entries — never in deck/review core.

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
  chapter_ref text                     -- dobson chapter that introduces it
);
create table if not exists lessons (
  id text primary key,
  seq integer not null unique,
  title text not null,
  chapter_ref text,                    -- 'dobson:12'
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
- Backups: the SQLite file lives under `data/`; `scripts/backup.cmd` zips `data/` to `E:\git\scriptorium\backups\` — consistent with the zip-at-repo-root backup habit.
- Sprint reports to `docs/reports/sprint-N.md`, shape: What shipped / What you need to do once / What's deferred / Verification.

---

# PHASE 1 — GENERIC DECK ENGINE

## Sprint 0 — Scaffold & skeleton

### RECON
Confirm `E:\git\scriptorium` is empty. Check nothing is listening on 5180 or 8012 (`netstat -ano | findstr "5180 8012"`). Read this brief top to bottom.

### BUILD
- Scaffold frontend (Vite + React + TS) in `web/`, backend (FastAPI) in `service/`. Repo layout:
  ```
  scriptorium/
    BUILD_BRIEF.md
    README.md                # written for Jess-the-user, not devs
    RUNBOOK.md               # ports, start/stop, backup, task scheduler
    docs/reports/
    docs/generation/rejects/
    data/                    # scriptorium.db lives here (gitignored)
    scripts/                 # start-service.cmd, start-web.cmd, backup.cmd
    service/app/             # main.py, db.py, card_types.py, routers/
    web/src/
      pages/  components/  hooks/
      lib/                   # framework-free
      config/cardTypes.ts
      theme.css
  ```
- `service/app/db.py`: SQLite connection (WAL, Row factory), idempotent schema bootstrap from the DDL above, run on startup.
- Health endpoint `GET /api/health` returning `{ok, db, version}`; frontend fetches and renders it.
- `theme.css` design tokens (colors, spacing, type scale) + `@font-face` for chosen Greek-capable serif. One sample page proving polytonic Greek renders: display `ἐν ἀρχῇ ἦν ὁ λόγος, ᾧ ῥῆμα`.
- `.env.example` heavily commented: ports, `PYTHONUTF8=1`, and the shouting block: `# LEAVE ANTHROPIC_API_KEY UNSET — if set, the Agent SDK silently bills API credits instead of the Max plan.`
- `scripts/*.cmd` wrappers; RUNBOOK documenting port claims 5180/8012.

### VERIFY (do this, don't skip)
- Both processes start via the `.cmd` wrappers; health check green in the UI.
- Polytonic test string round-trips: POST it to a scratch endpoint, store in SQLite, read back, render — byte-identical (NFC).
- Pinned versions recorded in the sprint report.

## Sprint 1 — Decks, cards, card-type registry

### RECON
Read `db.py`, the DDL, and Divergence Rules 1/2/6.

### BUILD
- Backend CRUD: decks (create/rename/soft-delete/list), cards (create/edit/soft-delete/list by deck). Central data access in `service/app/routers/` calling small query functions — no inline SQL in route bodies.
- Card-type registries, both sides, with two launch types:
  - `basic`: `{front, back, hint?}`
  - `cloze`: `{text, deletions: [{start,end}]}` — one card per deletion at review time.
- Payload validation against the registry schema on write (backend) and defensive `safePayload` on read (frontend `lib/`).
- Frontend: Decks page (grid of decks + counts), Deck page (card list, add/edit modal). Manual card authoring works end to end.
- `web/src/lib/` starts framework-free: `ids.ts`, `sanitize.ts`, `clozeSplit.ts` with file-header notes.

### VERIFY (do this, don't skip)
- Create a deck, add basic + cloze cards, edit, soft-delete, restore-by-hand in SQLite — UI never crashes on a hand-corrupted payload (test one).
- `node --test` (or Vitest) runs on `lib/clozeSplit.ts` and `lib/sanitize.ts` in plain Node — proves the seam.

## Sprint 2 — FSRS drill loop

### RECON
Read `py-fsrs` docs/API for the pinned version. Read Divergence Rule 3.

### BUILD
- `service/app/scheduler.py` wrapping py-fsrs: `next_due(deck_id, limit)`, `grade(card_id, rating)` updating `card_state` + `review_log` atomically.
- Review endpoints: `GET /api/review/queue?deck_id=`, `POST /api/review/grade`.
- Frontend Review page: front → reveal → four-button grade (Again/Hard/Good/Easy), keyboard shortcuts (space = reveal, 1–4 = grade). Session summary (reviewed/again-count/streak).
- Daily queue mixes due reviews + configurable new-cards/day (deck `config.newPerDay`, default 10).
- Stats endpoint + simple Deck page numbers: due today, new remaining, retention estimate.

### VERIFY (do this, don't skip)
- Seed 30 cards via a script; simulate 3 “days” of reviews by faking timestamps in a scratch script; confirm intervals grow for Good/Easy and reset for Again.
- Keyboard-only review session works start to finish.

## Sprint 3 — Verse-memory + import/export (generic engine ships here)

### RECON
Read the card-type registries and Review page.

### BUILD
- Card type `verse`: `{reference, translation, text}` with two review renderings: full-cloze (recite from reference alone) and **first-letters** mode (show first letter of each word as the hint) — mode is per-card-state, graduating from first-letters to full recall after N successful reviews (store in payload or config; Fable picks, notes it).
- Deck import/export: JSON (canonical) and CSV (basic cards only). Parse-then-confirm import flow (show what will be created before committing).
- Deck topics/tags surfaced in UI so science decks, verse decks, Greek decks coexist legibly.
- README.md for Jess: what it is, how to start it, how to make her first deck.

### VERIFY (do this, don't skip)
- Build a real 5-verse deck (any public-domain translation, e.g. KJV/WEB) and a 10-card science deck by hand; drill both; first-letters mode graduates correctly.
- Export → wipe → import round-trip preserves decks, cards, and (explicitly) FSRS state.

**Phase 1 exit:** Scriptorium is a usable general flashcard app with proper spaced repetition. Jess can live in it while Phases 2–3 are built.

---

# PHASE 2 — CORPUS & GENERATION

## Sprint 4 — MorphGNT ingest

### RECON
Fetch MorphGNT SBLGNT from its GitHub repo; read its README + LICENSE and record license terms. Inspect the file format (one token per line: book/chapter/verse, parse code, surface forms, lemma).

### BUILD
- `service/app/ingest/morphgnt.py`: parse the source files into `corpora` + `corpus_tokens` (store parse codes verbatim; NFC-normalize all Greek), then compute `lemma_freq` (count + dense rank).
- `scripts/ingest-morphgnt.cmd` one-shot runner; idempotent (wipe-and-reload that corpus_id).
- Read-only corpus endpoints: token lookup by ref (`/api/corpus/ref/John.1.1`), lemma search, frequency slice (`/api/corpus/lemmas?rank_from=1&rank_to=50`).
- Corpus browser mini-page (dev tool, unpolished): pick a verse, see tokens with lemma + parse.
- README attribution section for the corpus license.

### VERIFY (do this, don't skip)
- Token count within expected magnitude for the Greek NT (~138k tokens); John 1:1 tokens display with correct lemmas (λόγος present, article ὁ parsed as such — eyeball against any printed GNT).
- Frequency top-10 sanity check: ὁ, καί, αὐτός should dominate.

## Sprint 5 — Generation pipeline + verification cycle

### RECON
Read `claude-agent-sdk` (Python) docs for the pinned version: query API, model selection, subscription auth notes. Confirm `claude` CLI login works on this machine and `ANTHROPIC_API_KEY` is unset in the service environment. ⚠️ GATE A must be resolved (default: Sonnet generates, different model verifies).

### BUILD
- `service/app/gen/` — the pipeline, runnable headless via `scripts/generate.cmd` and from an admin endpoint:
  1. **Generate.** Prompt template receives: task spec (e.g. "vocab cards for lemma ranks 41–60" or "parsing cards: every present active indicative in John 1"), the *actual corpus rows* (lemmas, surfaces, parse codes, refs) selected by SQL — the model arranges and glosses grounded material rather than recalling Greek. Output: strict JSON card candidates, each with `source.citations: [corpus_token_ids]`.
  2. **Validate (programmatic, no model).** Every citation resolves; cited surface/lemma appears in the card where claimed; parse fields on parsing cards match the token's stored parse code exactly; glosses non-empty; JSON schema-valid. Any failure → `docs/generation/rejects/<batch>/<card>.json` with reason.
  3. **Verify (second model — GATE A choice).** Survivors go to the verifier with the same corpus rows: check gloss accuracy, pedagogical sanity, difficulty labeling. Verifier returns pass/fail+reason per card; fails join the rejects.
  4. **Land.** Survivors insert as cards (types `vocab_gk`, `parsing` — add both to the registries this sprint) into a target deck, `source` json carrying citations + batch id + model ids.
- Batch ledger table (`gen_batches`) recording spec, models, counts (generated/validated/verified/landed), timestamps.

### VERIFY (do this, don't skip)
- Run a real batch: vocab ranks 1–40 + parsing cards from John 1. Inspect 10 landed cards by hand against the corpus browser.
- Deliberately corrupt one candidate (bad citation) in a test run — confirm it lands in rejects with the right reason, not in the deck.
- Confirm the batch billed subscription, not API (no `ANTHROPIC_API_KEY` present; note SDK-reported model/usage in the report).

## Sprint 6 — Machen syllabus map + chapter deck generation

### RECON
Read `concepts`/`lessons` DDL. ⚠️ GATE C must be resolved (default: Machen). Obtain the public-domain text of Machen, *New Testament Greek for Beginners* (1923) — CCEL/Archive.org host it; verify the edition is the 1923 PD original, record source URL + confirmation in the sprint report. If PD status can't be confirmed for the copy found, STOP and flag rather than proceeding.

### BUILD
- `data/syllabus_map.greek.json` format + loader → populates `concepts` (with `chapter_ref`) and a stub `lessons` row per chapter. Format (language-agnostic; Hebrew reuses it later):
  ```json
  { "language": "greek", "source": "machen-1923", "source_is_pd": true,
    "chapters": [
    { "n": 12, "title": "…",
      "concepts": [{"id": "GK.PRES.ACT.IND", "name": "Present active indicative"}],
      "vocab_lemmas": ["λέγω", "…"],
      "reading_ref": "machen:12",
      "notes": "constructions to prefer/avoid in generated practice" }
  ] }
  ```
- **Auto-draft the Greek map** via the Sprint 5 pipeline pattern: chunk Machen's text by lesson, extract each lesson's vocab list and grammar topics into map entries, normalize lemmas against the corpus. Same three-pass discipline: draft → programmatic validation (every lemma exists in MorphGNT; concept ids from the registry) → second-model verify (extraction fidelity: did the map miss a topic the chapter teaches?). Output lands as a *draft* flagged `"reviewed": false` per chapter — the loader warns loudly on unreviewed chapters but does not block.
- Store Machen's per-lesson text (explanations, exercises, readings) in a `source_texts` table keyed by `reading_ref`, so lessons can render it in-app. **PD-only guardrail in code:** the loader refuses `source_texts` rows for any map with `"source_is_pd": false` — this is what keeps the future Dobson/Hebrew map honest by construction.
- `scripts/build-chapter.cmd greek N`: given a reviewed chapter, generate (via the Sprint 5 pipeline) that chapter's vocab deck + parsing deck, constrained to its lemmas/concepts plus all previously introduced ones.
- Validation: loader rejects lemmas absent from the corpus (typo guard) with a friendly error listing near-matches.

### VERIFY (do this, don't skip)
- Auto-draft runs end to end; spot-check 3 chapters' vocab lists against the actual Machen text side by side.
- Run build-chapter on a reviewed chapter; decks appear correctly scoped.
- Feed the loader a misspelled lemma — near-match error fires. Feed it a `source_is_pd: false` map with source_texts — refusal fires.

**What Jess does once (flagged in report):** review the auto-drafted map — skim each chapter entry against Machen's text, fix misses, flip `"reviewed": true`. This replaces the authoring evening; expect an hour or two, not an evening.

---

# PHASE 3 — LESSON ENGINE

## Sprint 7 — Lessons & mastery

### RECON
Read `lessons`, `lesson_items`, `concept_mastery` DDL and the syllabus-map loader.

### BUILD
- Lesson assembly: for each mapped chapter, `lesson_items` = `read` → `drill` (chapter vocab deck) → `drill` (parsing deck) → `translate`/`compose` placeholders (Sprint 8/9). The `read` item renders in-app from `source_texts` when the source is PD (Greek/Machen); otherwise it renders a pointer ("Read <book> ch. N — <title>") — this is the only place the PD distinction touches the UI, and it's data-driven, not branched per language.
- Mastery model in framework-free `lib/mastery.ts` mirrored in `service/app/mastery.py` (single source of truth: implement in Python, port the pure function, test both against shared JSON fixtures):
  - Concept score updates from parsing-card reviews (rating → delta) and later from checker results; gentle time decay.
  - Lesson `active → mastered` when: its decks' cards average FSRS state ≥ review with retention estimate ≥ threshold (deck config, default 0.9) AND its concepts ≥ 0.8. Next lesson unlocks on mastery.
- Lessons page: spiral-visible UI — mastered lessons show live due-counts (FSRS keeps them warm forever); active lesson shows its item sequence; locked lessons greyed.
- Manual override: Jess can force-unlock or re-lock a lesson (she outranks the model of her own mastery).

### VERIFY (do this, don't skip)
- Fixture-driven tests: mastery function identical outputs in Node and Python from shared fixtures.
- Simulated review history flips a lesson to mastered and unlocks the next; override buttons work.

## Sprint 8 — Reading & translation + the checker

### RECON
Read the Sprint 5 pipeline and Divergence Rule 4. The checker is the highest-stakes AI surface in the app: Jess is a beginner and cannot always spot a wrong correction. Citation validation is load-bearing.

### BUILD
- Exercise generation (pipeline extension): `translate_gk_en` — select real corpus passages constrained to introduced vocab/concepts (SQL over `corpus_tokens` + map); store prompt with token refs and a verified answer key (English rendering, generated then verifier-checked).
- Reading page: passage displayed in Greek (tap a word → lemma + parse from corpus, no model call), textarea for Jess's translation, submit.
- Checker endpoint: prompt = her submission + the passage's *full token rows inline* (surface/lemma/parse/gloss) + answer key. Output: strict JSON — per-clause verdicts, each error tagged with the corpus token id it concerns and a one-line why. **Programmatic validation before display:** every cited token id must belong to the passage; corrections referencing forms must match stored parse codes; anything failing → the correction is dropped, logged to rejects, and the UI shows "one note was withheld (failed verification)" so silence is visible.
- Feedback UI: her text with inline highlights, expandable why-notes, links into the corpus browser. Score updates `concept_mastery` per tagged concept.
- Every displayed correction footnoted: "checked against MorphGNT <ref>".

### VERIFY (do this, don't skip)
- Submit a deliberately wrong translation (mistranslate a dative) — checker flags it with a citation that resolves to the right token.
- Submit a *correct* translation phrased unusually — confirm the checker doesn't invent errors (run twice; note stability in the report).
- Tamper test: hand-edit a checker response in a scratch harness to cite a token outside the passage — validation withholds it and the withheld-note UI appears.

## Sprint 9 — Composition (English → Greek)

### RECON
⚠️ GATE B must be resolved (default: transliteration widget). Read `lib/` conventions — the transliterator is pure logic.

### BUILD
- `lib/translit.ts`: deterministic Latin→Greek transliteration with live preview (`logos` → λόγος; support breathings/accents via markup like `)a` / `a/`, scheme documented in-app; beta-code accepted as fallback). Framework-free, fixture-tested (this one gets real Vitest coverage — data integrity is personal here).
- Exercise kind `compose`: English prompt generated from a real corpus sentence *held back as the answer key* (so every prompt has an attested Greek answer), constrained to introduced vocab/concepts per the syllabus map notes.
- Compose page: prompt, transliteration input with live Greek preview, submit → checker (Sprint 8 machinery; answer key = the attested sentence; checker instructed that *valid alternatives* to the attested rendering are acceptable — verdicts must distinguish "wrong" from "different but attested pattern," citing corpus parallels for the latter).
- Session flow: lesson items now run read → drill → translate → compose end to end.

### VERIFY (do this, don't skip)
- Transliteration fixtures pass (include ᾧ-class hard cases: iota subscript, rough breathing + accent stacking).
- Full lesson walkthrough on a stub chapter: every item kind reachable, mastery moves, checker feedback renders with citations.

---

# PHASE 4 — HORIZON (build only when Phase 3 is lived-in)

## Sprint 10 — Graded NT reader

- Known-lemma set = lemmas whose cards sit at FSRS review-state with retention ≥ threshold.
- Passage ranker: SQL scoring every pericope by % known lemmas; Reader page serves the next passage ≥ 95% known (slider), unknown words tap-to-reveal and one-tap add-to-deck (card generated via the pipeline, cited).
- This is the endgame loop: read real text, harvest gaps, drill, read further.

## Hebrew seam — SEAM ONLY, no implementation
- `corpus_id` already scopes tokens/frequency; card types `vocab_hb`/`parsing_hb` and an OSHB ingest module are future registry entries + one ingest file. The syllabus map format already carries Hebrew: `syllabus_map.hebrew.json` with `source: "dobson-lbh"`, `source_is_pd: false` (Jess owns the book; hand-built map, pointer-only reading items — the loader enforces this). RTL/niqqud rendering is the real work and is **not started** until Greek is in daily use. Do not scaffold empty Hebrew files; this paragraph is the seam.

---

# What Jess does once (collected)
1. `claude` login on dreammachine; confirm `ANTHROPIC_API_KEY` is unset in the service environment (Sprint 5 blocks on this).
2. Review the auto-drafted `data/syllabus_map.greek.json` against Machen's text and flip chapters to `"reviewed": true` (after Sprint 6; an hour or two; still the highest-leverage file in the repo). The Dobson Hebrew map remains a future hand-authoring evening when the Hebrew phase starts.
3. Resolve GATE A (model pair) before Sprint 5, GATE B (input method) before Sprint 9, and GATE C (Greek syllabus source) before Sprint 6 — defaults stand if unstated.
4. Add Task Scheduler entries per RUNBOOK when she wants it always-on.
