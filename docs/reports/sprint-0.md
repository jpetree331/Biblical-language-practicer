# Sprint 0 — Scaffold & skeleton

## What shipped

- Repo skeleton per the master plan: `web/` (Vite + React + TS, port 5180
  strictPort, `/api` proxied to 8012), `service/` (FastAPI + uvicorn, port
  8012, venv at `service/.venv`), `data/`, `scripts/`, `docs/reports/`,
  `docs/generation/rejects/`, `backups/`.
- `service/app/db.py`: SQLite at `data/scriptorium.db`, WAL mode, Row factory,
  idempotent bootstrap of the full master-plan DDL (plus `gen_batches` and two
  corpus indexes) at startup, `nfc()` helper.
- `GET /api/health` returning `{ok, db, version}`; frontend fetches and renders it.
- `POST /api/dev/roundtrip` — the Unicode canary endpoint (kept permanently).
- `web/src/theme.css` design tokens: paper/ink/oxblood palette, green/amber/red
  reserved for mastery status, Playfair Display (headings), Libre Franklin (UI),
  Noto Serif (Greek). Sample page renders `ἐν ἀρχῇ ἦν ὁ λόγος, ᾧ ῥῆμα`.
- `scripts/start-service.cmd`, `start-web.cmd`, `backup.cmd` (all set
  `PYTHONUTF8=1` where Python runs), `.env.example` with the shouting
  ANTHROPIC_API_KEY block, `RUNBOOK.md` documenting the 5180/8012 port claims,
  `README.md` stub, `BUILD_BRIEF.md` saved from the master plan.

## Pinned versions (locked)

Frontend (`web/package.json`, exact — no `^`/`~`): react/react-dom **19.2.8**,
vite **8.2.0**, typescript **6.0.2**, @vitejs/plugin-react **6.0.4**,
@types/react **19.2.17**, @types/react-dom **19.2.3**, @types/node **24.13.3**,
oxlint **1.75.0**, @fontsource/{playfair-display,libre-franklin,noto-serif}
**5.3.0**.

Backend (`service/requirements.txt`, frozen): fastapi **0.141.1**, uvicorn
**0.52.3**, fsrs (py-fsrs) **6.3.2**, claude-agent-sdk **0.2.137**, pydantic
**2.13.4**. Python **3.13.12**.

## Divergences from the master plan (flagged)

1. **Repo location**: `E:\git\Language-Learning` (pushed to
   `jpetree331/Biblical-language-practicer`), not `E:\git\scriptorium` — Jess
   invoked the build here and supplied this GitHub remote.
2. **Python 3.13, not 3.12** — 3.12 is not installed on dreammachine; every
   dependency supports 3.13.
3. **Greek font: Noto Serif, not SBL Greek** (the Fable-choice the plan
   delegated): SBL Greek's license does not permit redistribution, and this
   repo is public on GitHub. Noto Serif is OFL, self-hosted via @fontsource,
   and covers Greek Extended (polytonic) fully.
4. The Vite scaffold ships `oxlint` instead of eslint now; kept as-is.

## What you need to do once

Nothing yet. (Task Scheduler entries are optional and documented in RUNBOOK.md.)

## What's deferred

- Real pages/routing (Sprint 1). The current page is the health + Greek proof.
- Visual eyeball of the Greek font on your screen — verified via DOM text and
  byte-identity, but glance at http://localhost:5180 once and confirm the
  breathings/subscripts look right to you.

## Verification

- Both processes start via their `.cmd` wrappers; health renders green in the
  UI through the Vite proxy (confirmed by reading the served page).
- Polytonic round-trip: `ἐν ἀρχῇ ἦν ὁ λόγος, ᾧ ῥῆμα` POSTed → stored in SQLite
  → read back → `nfc_byte_identical: true`.
- `npm run build` (tsc + vite) passes clean.
- Ports 5180/8012 were confirmed free before claiming.
