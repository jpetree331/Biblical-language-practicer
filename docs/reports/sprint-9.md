# Sprint 9 — Composition (English → Greek)

## GATE B (resolved by default, flagged)

**Transliteration widget** with live preview, beta-code-flavored scheme
(documented in-app): letters `q→θ c→χ y→ψ h→η w→ω x→ξ`, breathings *before*
a letter (`)a` → ἀ, `(a` → ἁ), accents *after* (`a/ a\ a=`), iota subscript
`a|`, diaeresis `i+`, automatic final sigma. `lo/gos` → λόγος. The OS
Polytonic keyboard remains usable — the textarea accepts Greek directly too
(translit passes Greek characters through unchanged).

## What shipped

- **`web/src/lib/translit.ts`** — deterministic, framework-free, with real
  fixture coverage including the plan's named hard cases: `(w=|` → ᾧ (rough
  breathing + circumflex + iota subscript), `)arch=|` → ἀρχῇ, `(rh=ma` → ῥῆμα;
  a full clause round-trips **NFC-identical** to the corpus form of
  John 1:1a. 7/7 fixture groups pass in plain Node.
- **Compose exercises** (same generator as Sprint 8): the English prompt is
  generated *from* a real corpus sentence held back as the answer key — every
  prompt has an attested Greek answer with citations. Coverage-constrained
  (≥90% known lemmas, 4–12 tokens).
- **Compose page**: English prompt, transliteration input with live Greek
  preview, submit → the Sprint 8 checker with its composition instruction:
  valid alternatives to the attested rendering are acceptable; verdicts must
  distinguish "wrong" from "different but attested pattern" (the latter are
  nitpicks pointing at the attested form).
- **Session flow**: lesson items now run read → drill → translate → compose
  end to end on one page per lesson, with per-exercise last scores.

## What you need to do once

Nothing. (If the transliteration scheme fights your fingers, say so — the
mapping table is one object in `translit.ts`.)

## What's deferred

- On-screen scheme cheatsheet is a single line; a fuller reference card could
  live on the About page.
- Checker "attested parallel" citations for alternative renderings cite the
  exercise's own passage; cross-corpus parallels (other verses with the same
  construction) are future work.

## Verification

- Transliteration fixtures: **7/7** including iota subscript and rough
  breathing + accent stacking; NFC byte-identity against corpus text.
- Compose flow live: submitted the attested rendering of Acts 13:30 (as the
  widget would produce it) → score **1.0**, praise notes, zero withheld;
  checker's citations all resolve.
- Full lesson walkthrough (lesson 8, in the running UI): every item kind
  reachable — Machen reading in-app, drill slots (honest "not built yet"
  pointer with the exact command), 2 translate passages (one showing
  "last: 92%"), 2 compose prompts (one "last: 100%"), concept bars rendering.
- Mastery moves from checker results (GK.IMPF.ACT.IND updated by the John 1:1
  submissions; visible in the lesson's concept bars).
