/* Runs in plain Node (node --test) — proves lib/ stays framework-free. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { decodeParse } from './parseCode.ts'

test('verb with person/tense/voice/mood/number', () => {
  assert.equal(decodeParse('V- 3IAI-S--'), 'verb — 3rd person imperfect active indicative singular')
})

test('noun with case/number/gender', () => {
  assert.equal(decodeParse('N- ----DSF-'), 'noun — dative singular feminine')
})

test('article', () => {
  assert.equal(decodeParse('RA ----NSM-'), 'definite article — nominative singular masculine')
})

test('bare conjunction', () => {
  assert.equal(decodeParse('C- --------'), 'conjunction')
})

test('malformed codes come back verbatim', () => {
  assert.equal(decodeParse('garbage'), 'garbage')
  assert.equal(decodeParse('ZZ --------'), 'ZZ --------')
})
