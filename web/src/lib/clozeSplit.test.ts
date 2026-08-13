/* Runs in plain Node (node --test), no bundler — proves lib/ is framework-free. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clozeSplit, normalizeDeletions, parseClozeMarkup, toClozeMarkup } from './clozeSplit.ts'

test('parseClozeMarkup extracts deletions with correct offsets', () => {
  const { text, deletions } = parseClozeMarkup('the [[quick]] brown [[fox]]')
  assert.equal(text, 'the quick brown fox')
  assert.deepEqual(deletions, [
    { start: 4, end: 9 },
    { start: 16, end: 19 },
  ])
})

test('parseClozeMarkup round-trips through toClozeMarkup', () => {
  const marked = 'ὁ [[λόγος]] ἦν πρὸς τὸν [[θεόν]]'
  const { text, deletions } = parseClozeMarkup(marked)
  assert.equal(toClozeMarkup(text, deletions), marked)
})

test('parseClozeMarkup rejects bad markup', () => {
  assert.throws(() => parseClozeMarkup('no deletions here'))
  assert.throws(() => parseClozeMarkup('unclosed [[oops'))
  assert.throws(() => parseClozeMarkup('empty [[]] brackets'))
})

test('clozeSplit produces ordered segments covering the whole text', () => {
  const text = 'alpha beta gamma'
  const segs = clozeSplit(text, [
    { start: 6, end: 10 },
    { start: 0, end: 5 },
  ])
  assert.equal(segs.map((s) => s.text).join(''), text)
  assert.deepEqual(
    segs.map((s) => s.deletion),
    [0, null, 1, null],
  )
})

test('normalizeDeletions drops out-of-range and overlapping spans', () => {
  const text = 'twelve chars'
  assert.deepEqual(
    normalizeDeletions(text, [
      { start: 0, end: 6 },
      { start: 3, end: 8 }, // overlaps first — dropped
      { start: 7, end: 99 }, // past end — dropped
      { start: 7, end: 12 },
    ]),
    [
      { start: 0, end: 6 },
      { start: 7, end: 12 },
    ],
  )
})
