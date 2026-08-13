# Sprint 4 — MorphGNT ingest

## What shipped

- `service/app/ingest/morphgnt.py`: parses all 27 MorphGNT SBLGNT files into
  `corpora` + `corpus_tokens` (surface as printed, normalized form, lemma, and
  the POS + parse code stored **verbatim** as one field, e.g. `N- ----NSF-`;
  all Greek NFC-normalized; `pos` = 1-based word position in verse), then
  computes `lemma_freq` (count + dense rank). Idempotent: wipes and reloads
  `corpus_id='sblgnt'` each run.
- `scripts/ingest-morphgnt.cmd`: clones the corpus repo into `data\` on first
  run (gitignored — corpus files are never committed), then ingests.
- Read-only corpus endpoints: `/api/corpus/ref/John.1.1`,
  `/api/corpus/lemmas?rank_from=&rank_to=`, `/api/corpus/lemma/{lemma}`,
  `/api/corpus/books`, `/api/corpus/info` (includes recorded license).
- Corpus browser mini-page (`#/corpus`, deliberately unpolished dev tool):
  book/chapter/verse pickers → token table (surface, lemma clickable for
  occurrence counts, parse code, gloss column awaiting Sprint 5).
- README attribution section + license recorded in the `corpora` table at
  ingest: SBLGNT text under the SBLGNT EULA; morphological parsing +
  lemmatization CC-BY-SA 3.0; citation Tauber (ed.), MorphGNT: SBLGNT Edition
  v6.12, DOI 10.5281/zenodo.376200.

## Divergences / choices

- Book abbreviations are SBL-style (`Matt`, `1Cor`, `John`…), used in refs as
  `Book.C.V`.
- `parse` stores POS + parsing code together (both columns of the source,
  verbatim) — nothing is interpreted at ingest time.

## What you need to do once

Nothing — the corpus is already ingested on dreammachine.

## What's deferred

- Glosses (`corpus_tokens.gloss`) stay NULL until the Sprint 5 generation
  pipeline fills them (validated).
- Hebrew/OSHB: seam only, untouched, per plan.

## Verification

- **137,554 tokens** ingested from 27 files (expected magnitude ~138k), 5,461
  lemmas, in 0.7s.
- John 1:1 eyeballed against a printed GNT: `Ἐν ἀρχῇ ἦν ὁ λόγος…` — λόγος
  lemma present (positions 5/8/17), the article ὁ parsed `RA ----NSM-`
  (definite article, nom. sg. masc.), ἦν → εἰμί `V- 3IAI-S--`. All correct.
- Frequency top-10 sanity: **ὁ (19,769), καί (8,973), αὐτός (5,546)** dominate,
  exactly as expected; rest of top-10 (σύ, δέ, ἐν, ἐγώ, εἰμί, λέγω, εἰς) all
  plausible.
- Corpus browser renders the verse + full token table in the running UI.
- Dev-loop note: Vite's watcher on Windows twice served stale modules after
  rapid multi-file edits; documented the restart remedy in RUNBOOK.md.
