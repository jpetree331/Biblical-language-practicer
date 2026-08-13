# Scriptorium

A spaced-repetition flashcard app with a Biblical Greek curriculum growing
inside it. Local-first: everything runs on this machine, works offline, and
stores its data in a single SQLite file.

*(This README grows with the app; the full user guide lands in Sprint 3.)*

## Start it

Run each in its own window:

```
scripts\start-service.cmd
scripts\start-web.cmd
```

Then open **http://localhost:5180**. Operational details: `RUNBOOK.md`.

## What's here so far

- **Sprint 0** — skeleton: frontend (Vite + React, port 5180), backend
  (FastAPI + SQLite, port 8012), warm bookish theme, polytonic Greek proven to
  round-trip through the whole stack.

## Corpus attribution

*(placeholder — filled at MorphGNT ingest, Sprint 4)*
