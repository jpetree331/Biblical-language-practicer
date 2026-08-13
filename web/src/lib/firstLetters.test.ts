/* Runs in plain Node (node --test) — proves lib/ stays framework-free. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { firstLetters } from './firstLetters.ts'

test('english words reduce to first letters', () => {
  assert.equal(firstLetters('In the beginning was the Word'), 'I t b w t W')
})

test('punctuation and line breaks survive', () => {
  assert.equal(firstLetters('Hello, world!\nNew line.'), 'H, w!\nN l.')
})

test('polytonic greek keeps its diacritics on the first letter', () => {
  assert.equal(firstLetters('ἐν ἀρχῇ ἦν ὁ λόγος'), 'ἐ ἀ ἦ ὁ λ')
  assert.equal(firstLetters('ᾧ ῥῆμα, θεός'), 'ᾧ ῥ, θ')
})

test('numbers count as word characters', () => {
  assert.equal(firstLetters('John 3:16 says'), 'J 3:1 s')
})
