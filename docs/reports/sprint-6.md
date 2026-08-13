# Sprint 6 — Machen syllabus map + chapter deck generation

## GATE C (resolved by default, flagged)

**Machen, *New Testament Greek for Beginners*, Macmillan, 1923** — public
domain. PD basis: published in the USA in 1923; US copyright expired (PD since
2019). Source copy: Internet Archive item
[`newtestamentgree00mach`](https://archive.org/details/newtestamentgree00mach)
(1923 Macmillan edition confirmed in item metadata; openly downloadable, no
lending restriction). Full-text OCR fetched from
`https://archive.org/download/newtestamentgree00mach/newtestamentgree00mach_djvu.txt`
to `data/machen/` (gitignored). Provenance is also recorded inside the map
under `source_provenance`.

## What shipped

- `service/app/ingest/machen.py`: splits the OCR text into Machen's **33
  lessons** despite heading corruption (`_ LESSON XXI`, `LESSON XXV ;`,
  `ἦ LESSON ΧΧΙΧ` with Greek homoglyphs, XXXIII misread as XXXII — order of
  appearance is authoritative, numerals are sanity-checks). Lessons stored in
  the new `source_texts` table (`machen:N`), so lessons can render Machen
  in-app.
- **Auto-drafted `data/syllabus_map.greek.json`** (committed — a gitignore
  exception; it's the highest-leverage file in the repo) via the Sprint 5
  three-pass discipline:
  - *Draft*: claude-sonnet-5 per lesson — title, concepts (documented
    `GK.*` id convention), vocabulary lemmas (dictionary forms, OCR-corrupted
    Greek restored), generation notes.
  - *Programmatic validation*: every lemma checked against MorphGNT;
    unambiguous near-matches auto-corrected (recorded), casualties flagged in
    `validation_notes` (13 chapters have notes).
  - *Verify*: claude-opus-5 checked extraction fidelity per chapter — missed
    topics / invented vocab — findings attached as `verifier_notes` (20
    chapters have notes; they are advisory annotations for your review, not
    silent rejections).
  - Every chapter lands `"reviewed": false`.
  - Totals: 33 chapters, 430 corpus-validated lemmas, 133 concepts.
- **Loader** `service/app/curriculum.py` (`scripts\load-syllabus.cmd`):
  populates `concepts` + stub `lessons` rows (lesson 1 active, rest locked);
  warns loudly per unreviewed chapter; **hard-fails** on any lemma absent from
  the corpus with a near-match hint; **PD guardrail in code** — a map with
  `source_is_pd: false` is refused outright if in-app `source_texts` exist for
  its reading_refs (this is what keeps the future Dobson/Hebrew map honest).
- **`scripts\build-chapter.cmd greek N`**: refuses unreviewed chapters
  (`--force` to override); builds the chapter vocab deck (its own lemmas) and
  parsing deck(s) — corpus-wide tokens matching the chapter's verb concepts
  (`GK.<TENSE>.<VOICE>.<MOOD>` → MorphGNT pattern) restricted to lemmas
  introduced in chapters 1..N, all through the Sprint 5 cited-and-verified
  pipeline.

## What you need to do once (the flagged evening-replacement)

**Review the draft map** — skim each chapter of
`data/syllabus_map.greek.json` against Machen (the text is in the app's
`source_texts`, or any printed copy), fix what the `validation_notes` /
`verifier_notes` flag, and flip `"reviewed": true` per chapter. Expect an hour
or two. `build-chapter` unlocks per chapter as you flip them.

## What's deferred

- Lesson assembly/mastery/read-items (Sprint 7), checker (Sprint 8),
  composition (Sprint 9).
- The 3 verify-batch calls occasionally see truncated lesson bodies (7,000-char
  cap) — a few verifier notes honestly say "excerpt ends mid-section"; body
  caps can be raised when you want a deeper verify pass.

## Verification

- Splitter: 33/33 lessons, titles matching Machen's actual table of contents.
- Auto-draft ran end to end (33 draft calls + 5 verify batches, subscription
  auth). Spot-checks against the book text:
  - **ch.3** vocab = exactly the printed Lesson III list (βλέπω γινώσκω γράφω
    διδάσκω λαμβάνω λέγω λύω ἔχω — ἔχω restored from OCR `éxw`);
  - **ch.8** vocab correct (αὐτός ἐγώ δέ εἰμί σύ); verifier honestly flags
    excerpt truncation rather than inventing certainty;
  - **ch.31** δίδωμι-lesson vocab plausible and corpus-valid.
- Loader: loaded 33 chapters → 133 concepts, 33 lessons, 33 loud unreviewed
  warnings; misspelled-lemma test fires the near-match error
  (`λογος → did you mean: λόγος?`); `source_is_pd:false` + source_texts test
  fires the refusal. Both confirmed.
- `build-chapter greek 3` refused (unreviewed), then with `--force`: vocab deck
  **8/8 landed**, parsing deck 13 generated → **11 landed** (verifier culled a
  near-duplicate and a weak instance), every card carrying token citations.
