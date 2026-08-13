/* Runs in plain Node (node --test). The hard cases the plan names:
   iota subscript, rough breathing + accent stacking. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { translit } from './translit.ts'

test('plain word with automatic final sigma', () => {
  assert.equal(translit('logos'), 'λογος')
  assert.equal(translit('logos '), 'λογος ')
  assert.equal(translit('sofia'), 'σοφια') // internal sigma stays σ
})

test('accents', () => {
  assert.equal(translit('lo/gos'), 'λόγος')
  assert.equal(translit('qeo/s'), 'θεός')
  assert.equal(translit('kai\\'), 'καὶ')
})

test('breathings', () => {
  assert.equal(translit(')en'), 'ἐν')
  assert.equal(translit('(o'), 'ὁ')
  assert.equal(translit('(rh=ma'), 'ῥῆμα') // rough breathing on rho + circumflex
})

test('iota subscript and stacking — the ᾧ-class hard cases', () => {
  assert.equal(translit('(w=|'), 'ᾧ') // rough + circumflex + iota subscript
  assert.equal(translit(')arch=|'), 'ἀρχῇ') // smooth + circumflex + subscript mid-word
  assert.equal(translit('tw=|'), 'τῷ')
})

test('full clause round-trips NFC-identical to the corpus form', () => {
  const got = translit(')en )arch=| )h=n (o lo/gos')
  assert.equal(got, 'ἐν ἀρχῇ ἦν ὁ λόγος'.normalize('NFC'))
})

test('diaeresis and passthrough', () => {
  assert.equal(translit('i+'), 'ϊ')
  assert.equal(translit('abc 123, .'), 'αβχ 123, .')
})

test('capitals', () => {
  assert.equal(translit('Qeo/s'), 'Θεός')
  assert.equal(translit(')Ihsou=s'), 'Ἰησοῦς')
})
