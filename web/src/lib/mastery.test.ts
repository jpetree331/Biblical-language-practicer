/* Runs in plain Node (node --test). Fixture-driven: identical cases run
   against service/app/mastery.py — the twin must agree to 1e-9. */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { applyDecay, applyReview, lessonMastered } from './mastery.ts'

const fixtures = JSON.parse(
  readFileSync(join(import.meta.dirname, '../../../shared/mastery-fixtures.json'), 'utf-8'),
)

test('apply_review fixtures', () => {
  for (const { args, expected } of fixtures.apply_review) {
    const got = applyReview(args.score, args.rating)
    assert.ok(Math.abs(got - expected) < 1e-9, `applyReview(${args.score}, ${args.rating}) = ${got}, want ${expected}`)
  }
})

test('apply_decay fixtures', () => {
  for (const { args, expected } of fixtures.apply_decay) {
    const got = applyDecay(args.score, args.days)
    assert.ok(Math.abs(got - expected) < 1e-9, `applyDecay(${args.score}, ${args.days}) = ${got}, want ${expected}`)
  }
})

test('lesson_mastered fixtures', () => {
  for (const { args, expected } of fixtures.lesson_mastered) {
    const got = lessonMastered(
      args.deck_stats,
      args.concept_scores,
      args.retention_threshold,
      args.concept_threshold,
    )
    assert.equal(got, expected, `lessonMastered(${JSON.stringify(args)}) = ${got}`)
  }
})
