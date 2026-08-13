# RUNBOOK — Scriptorium

Operational notes. For what the app *is*, read `README.md`.

## Port claims (new, registered by this repo)

| Port | Process | Notes |
|------|---------|-------|
| **5180** | Vite dev server (frontend) | `strictPort: true` — fails loudly if taken |
| **8012** | FastAPI/uvicorn (backend) | bound to 127.0.0.1 only |

## Start / stop

Start (each in its own window, order doesn't matter):

```
scripts\start-service.cmd
scripts\start-web.cmd
```

Then open http://localhost:5180. Stop with Ctrl+C in each window.

Every Python entrypoint sets `PYTHONUTF8=1` inside its `.cmd` wrapper. If you
ever run the service by hand, set it first — polytonic Greek corrupts without it.

## Database

- Single SQLite file: `data\scriptorium.db` (WAL mode — you'll also see `-wal`/`-shm` files; that's normal).
- Schema bootstraps idempotently at service startup; there is no migration tool at this size.
- `data\` is gitignored. The DB never leaves this machine via git.

## Backup

```
scripts\backup.cmd
```

Zips `data\` to `backups\scriptorium-data-<timestamp>.zip`. Run it whenever you
care about what's inside; there is no automatic schedule unless you add one.

## Task Scheduler (optional, when you want it always-on)

Create two basic tasks (Run whether user is logged on or not, At log on):

1. **Scriptorium service** — Action: start a program → `E:\git\Language-Learning\scripts\start-service.cmd`
2. **Scriptorium web** — Action: start a program → `E:\git\Language-Learning\scripts\start-web.cmd`

Optionally a third running `backup.cmd` weekly.

## Corpus ingest

```
scripts\ingest-morphgnt.cmd
```

Clones MorphGNT SBLGNT into `data\morphgnt-sblgnt` (first run only) and loads
it into SQLite. Idempotent — re-running wipes and reloads the `sblgnt` corpus.

## Greek curriculum scripts

```
scripts\ingest-morphgnt.cmd        # corpus into SQLite (idempotent)
scripts\draft-syllabus.cmd         # auto-draft data\syllabus_map.greek.json from Machen
scripts\load-syllabus.cmd          # validate + load the map into concepts/lessons
scripts\build-chapter.cmd greek N  # generate a reviewed chapter's vocab+parsing decks
scripts\generate.cmd ...           # ad-hoc generation batches (see the file header)
```

The map's chapters carry `"reviewed": false` until you check them against
Machen and flip the flag; `build-chapter` refuses unreviewed chapters
(`--force` overrides while you experiment).

## Dev-loop quirk (Windows)

Vite's file watcher occasionally misses a change when several files are edited
in quick succession; the dev server then serves a stale module even after the
file is touched. If the UI seems to ignore fresh code, restart
`scripts\start-web.cmd` — the production build (`npm run build`) is never
affected.

## AI billing guardrail

`ANTHROPIC_API_KEY` must never be set in `.env`, the `.cmd` wrappers, or the
service environment — the Agent SDK would silently bill API credits instead of
the Max subscription. See the shouting block in `.env.example`.
