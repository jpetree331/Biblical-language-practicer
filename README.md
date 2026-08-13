# Scriptorium

A spaced-repetition flashcard app with a Biblical Greek curriculum growing
inside it. Local-first: everything runs on this machine, works offline, and
stores its data in one SQLite file. The scheduler is FSRS — the spiral method:
everything you master keeps resurfacing on its forgetting curve, forever.

## Start it

Run each in its own window:

```
scripts\start-service.cmd
scripts\start-web.cmd
```

Then open **http://localhost:5180**. To stop, Ctrl+C in each window.
Ports, backups, and Task Scheduler setup live in `RUNBOOK.md`.

## Make your first deck

1. **Decks → New deck.** Name it, give it a topic (topics group decks on the
   Decks page — `science`, `verses`, `greek`, anything).
2. **Add card.** Three card types:
   - **Basic** — front/back, with an optional hint.
   - **Cloze** — write a sentence and wrap the parts to blank out in
     `[[double brackets]]`. Each deletion becomes its own review.
   - **Verse memory** — reference + text. Early reviews show first-letter
     hints (`I t b w t W…`); after enough good reviews the card graduates and
     you recite from the reference alone.
3. **Review.** Space reveals, then grade yourself: `1` Again · `2` Hard ·
   `3` Good · `4` Easy. Be honest — the schedule is built from your answers.

New cards trickle in at **new/day** (set it on the deck page, default 10).
Reviews come due when FSRS predicts you're about to forget. A big due pile
after a break is normal; it clears faster than it looks.

## Import & export

- **Export** (deck page) writes a JSON file that carries everything, including
  each card's review schedule. **CSV** exports basic cards only.
- **Import** (top nav) takes either format, shows you exactly what will be
  created, and only commits when you confirm. Re-importing an export restores
  the deck *and* its schedule.

## The Greek curriculum

Phases 2–3 grow a Biblical Greek tutor inside this engine: the MorphGNT SBLGNT
corpus, generated vocab/parsing decks with every card cited back to real NT
tokens, Machen-sequenced lessons, translation exercises with an AI checker
that must cite the corpus to be believed. See `scriptorium_master_plan.md`.

## Corpus attribution

The Greek New Testament corpus is **MorphGNT SBLGNT**
(https://github.com/morphgnt/sblgnt):

> Tauber, J. K., ed. (2017) *MorphGNT: SBLGNT Edition*. Version 6.12
> [Data set]. DOI: 10.5281/zenodo.376200

The SBLGNT text itself is subject to the
[SBLGNT EULA](http://sblgnt.com/license/); the morphological parsing and
lemmatization are licensed
[CC-BY-SA 3.0](http://creativecommons.org/licenses/by-sa/3.0/). The corpus
files are **not** committed to this repository — `scripts\ingest-morphgnt.cmd`
clones them into `data\` (gitignored) and loads them into SQLite; the license
text above is also recorded in the `corpora` table at ingest.
