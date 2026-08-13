# Sprint 5 — Generation pipeline + verification cycle

## What shipped

- `service/app/gen/` — the four-stage pipeline (Divergence Rule 4 enforced):
  1. **Generate** (claude-sonnet-5, Agent SDK, subscription auth). SQL selects
     the actual corpus rows; the model only arranges and glosses them. For
     vocab it may cite only the sample token ids it was shown; for parsing it
     *selects* tokens and supplies in-context glosses — surface/lemma/parse/ref
     are copied from the DB rows it cites, never from model text.
  2. **Validate** (programmatic, no model): registry schema; every citation
     resolves; cited lemma matches; parsing cards' parse/surface/ref must equal
     the stored token exactly; glosses non-empty. Failures →
     `docs/generation/rejects/<batch>/validate-*.json` with reasons.
  3. **Verify** (claude-opus-5): gloss accuracy, data fidelity, pedagogical
     sanity; per-card pass/fail + one-line reason; fails join the rejects as
     `verify-*.json`.
  4. **Land**: survivors become cards (types `vocab_gk`, `parsing` — added to
     both registries) in the target deck with `source` carrying citations,
     batch id, and both model ids. Validated glosses also backfill
     `corpus_tokens.gloss` where NULL.
- `gen_batches` ledger (spec, models, generated/validated/verified/landed,
  timestamps); `GET /api/gen/batches`, `POST /api/gen/run`, and headless
  `scripts\generate.cmd` (argparse CLI).
- **Billing guardrail in code**: `ai.assert_subscription_auth()` raises if
  `ANTHROPIC_API_KEY` is present — the pipeline *refuses to run* rather than
  silently billing API credits.
- Frontend: `vocab_gk` and `parsing` registry entries with review renderings;
  `lib/parseCode.ts` decodes MorphGNT codes ("V- 3IAI-S--" → "verb — 3rd
  person imperfect active indicative singular"), framework-free + tested.

## GATE A (resolved by default, flagged)

**claude-sonnet-5 generates, claude-opus-5 verifies** — the plan's default
(Sonnet generates, a different model verifies), with Opus as the skeptic to
mirror the build/verify split. Swap `GENERATOR_MODEL`/`VERIFIER_MODEL` in
`service/app/gen/ai.py` if you want a different pair.

## What you need to do once

Nothing — `claude` login already works on dreammachine (verified live), and
the environment has no `ANTHROPIC_API_KEY`.

## What's deferred

- Difficulty labeling of generated cards (verifier checks sanity but no
  difficulty metadata is stored yet).
- A UI for launching batches — CLI/endpoint only for now.

## Verification (real batches, real models)

- **Vocab ranks 1–40** → 40 generated / 40 validated / **39 landed**; the
  verifier rejected μή glossed as bare "not" because it duplicated the οὐ card
  and lost the indicative/non-indicative distinction — a genuinely correct
  pedagogical catch. Ten landed cards hand-checked against the corpus:
  classroom-standard glosses (ὁ "the", εἰμί "to be", …), every citation
  resolves and lemma-matches.
- **Parsing, John 1, present active indicative** (`V- _PAI%`) → 20/20/18;
  rejects: a near-duplicate ἐστιν and a 2nd-plural ζητεῖτε whose gloss left
  the number unmarked. Landed samples all correct (φαίνει John 1:5
  `V- 3PAI-S--` "shines", εἶ John 1:19 `V- 2PAI-S--` "are you?").
- **Tamper tests** (scratch harness): fabricated token id → "citation 99999999
  does not resolve"; real token + wrong lemma → "lemma mismatch: token has
  'θεός', card claims 'λόγος'"; hand-tampered parse code → "parse mismatch …
  stored code is authoritative". All three written to rejects, none landed.
- **Billing**: `ANTHROPIC_API_KEY` confirmed unset; SDK-reported usage —
  vocab batch: generator 2,248 output tokens, verifier 5,134; parsing batch:
  1,163 / 3,922. Auth via Claude Code login (subscription).
- Two pipeline bugs found & fixed during the real runs: verifier commentary
  after its JSON array (extract_json now `raw_decode`s the first value) and an
  over-tight `max_turns=1` safety cap (now 4; still zero tools allowed).
- lib tests 23/23; `npm run build` clean.
