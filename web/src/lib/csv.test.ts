/* Runs in plain Node (node --test) — proves lib/ stays framework-free. */
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { basicCardsFromCsv, parseCsv, toCsvRow } from './csv.ts'

test('parseCsv handles quotes, commas, escaped quotes, CRLF', () => {
  const rows = parseCsv('a,"b,c","say ""hi"""\r\nd,e,f')
  assert.deepEqual(rows, [
    ['a', 'b,c', 'say "hi"'],
    ['d', 'e', 'f'],
  ])
})

test('toCsvRow round-trips through parseCsv', () => {
  const fields = ['plain', 'with,comma', 'with "quote"', 'multi\nline']
  assert.deepEqual(parseCsv(toCsvRow(fields))[0], fields)
})

test('basicCardsFromCsv detects header and skips bad rows with warnings', () => {
  const { cards, warnings } = basicCardsFromCsv('front,back,hint\nλόγος,word,John 1\n,missing\nx,y')
  assert.deepEqual(cards, [{ front: 'λόγος', back: 'word', hint: 'John 1' }, { front: 'x', back: 'y' }])
  assert.equal(warnings.length, 1)
  assert.match(warnings[0], /row 3/)
})

test('headerless csv works', () => {
  const { cards, warnings } = basicCardsFromCsv('a,b\nc,d')
  assert.equal(cards.length, 2)
  assert.equal(warnings.length, 0)
})
